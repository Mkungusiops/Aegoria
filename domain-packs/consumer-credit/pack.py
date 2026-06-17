"""Optional Python hooks for the consumer-credit domain-pack.

The pack is overwhelmingly declarative — the manifest *is* the onboarding. These
hooks exist only to back the two ``ModelSpec`` references in ``manifest.yaml``:

* :func:`fair_risk_score` — a self-contained logistic approval scorer.
* :func:`delinquency_forecast` — a light trend-extrapolation forecaster.

Both are pure NumPy (no scikit-learn / no heavyweight runtime) and both are
deliberately generic: they take plain feature/series inputs and return plain
arrays, so the core ML service can drive them through the ``remote`` runtime
without learning anything credit-specific.

Crucially, neither hook ever consumes a protected attribute. The scorer's
public surface only accepts the financial features declared safe in the
manifest (``income``, ``amount``); identifiers never reach it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

# Features the scorer is permitted to use. Anything not listed here — names,
# national ids, emails — is structurally excluded from the model input.
ALLOWED_FEATURES: tuple[str, ...] = ("income", "amount")

# Direct identifiers the scorer must never receive. Mirrors the manifest's
# ``protected_attributes`` so the guard and the policy can never drift.
PROTECTED_ATTRIBUTES: frozenset[str] = frozenset(
    {"applicant_name", "national_id", "email"}
)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable logistic function."""
    out = np.empty_like(z, dtype=np.float64)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    exp_z = np.exp(z[~pos])
    out[~pos] = exp_z / (1.0 + exp_z)
    return out


@dataclass
class FairRiskScorer:
    """A tiny, transparent logistic approval scorer.

    The model is a fixed-weight logistic regression over the *debt-to-income*
    relationship — higher income relative to the requested amount yields a
    higher approval probability. Weights are hand-set rather than trained so the
    reference pack ships without a model artifact, but the calling convention is
    identical to a trained model loaded via the ``remote`` runtime.
    """

    # Logit = bias + w_dti * log1p(income / amount). Calibrated so a DTI ratio
    # around 3x sits near a 0.5 approval probability.
    bias: float = -1.6
    w_dti: float = 1.15
    protected: frozenset[str] = field(default_factory=lambda: PROTECTED_ATTRIBUTES)

    def _features(self, income: np.ndarray, amount: np.ndarray) -> np.ndarray:
        amount = np.maximum(amount, 1.0)  # guard against divide-by-zero
        dti = np.log1p(np.maximum(income, 0.0) / amount)
        return dti

    def predict_proba(
        self, income: Sequence[float], amount: Sequence[float], **forbidden: object
    ) -> np.ndarray:
        """Return the approval probability for each application row.

        Any keyword that names a protected attribute raises immediately — the
        fairness contract is enforced in code, not merely documented.
        """
        leaked = self.protected.intersection(forbidden)
        if leaked:
            raise ValueError(
                f"protected attributes may not be passed to the scorer: {sorted(leaked)}"
            )
        income_arr = np.asarray(income, dtype=np.float64)
        amount_arr = np.asarray(amount, dtype=np.float64)
        if income_arr.shape != amount_arr.shape:
            raise ValueError("income and amount must have the same shape")
        logit = self.bias + self.w_dti * self._features(income_arr, amount_arr)
        return _sigmoid(logit)


def fair_risk_score(income: Sequence[float], amount: Sequence[float]) -> list[float]:
    """Manifest entry point for the ``fair_risk_scorer`` model.

    Accepts only the financial features the manifest marks as safe and returns
    a per-row approval probability in ``[0, 1]``.
    """
    return FairRiskScorer().predict_proba(income, amount).tolist()


def delinquency_forecast(days_past_due: Sequence[float], horizon_months: int = 3) -> list[float]:
    """Manifest entry point for the ``delinquency_forecaster`` model.

    Fits a least-squares line to one account's days-past-due series and
    extrapolates ``horizon_months`` ahead, clamped to the realistic ``[0, 180]``
    delinquency range. Returns the forecast for each future month.
    """
    series = np.asarray(days_past_due, dtype=np.float64)
    if series.size == 0:
        return [0.0] * max(0, horizon_months)
    if series.size == 1:
        # Not enough history for a trend; persist the last observation.
        return [float(np.clip(series[-1], 0.0, 180.0))] * max(0, horizon_months)

    t = np.arange(series.size, dtype=np.float64)
    slope, intercept = np.polyfit(t, series, deg=1)
    future_t = np.arange(series.size, series.size + max(0, horizon_months), dtype=np.float64)
    forecast = np.clip(intercept + slope * future_t, 0.0, 180.0)
    return forecast.tolist()
