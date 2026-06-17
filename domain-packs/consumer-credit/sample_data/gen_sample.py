#!/usr/bin/env python3
"""Generate fully synthetic sample data for the consumer-credit domain-pack.

Everything produced here is fake by construction:

* Names are ``Test User <n>`` — never a real person.
* National identifiers are the literal prefix ``SYN-`` plus a zero-padded index.
* Emails use the reserved ``example.test`` domain (RFC 6761 / RFC 2606 family),
  so they can never resolve to a live mailbox.

The generator is deterministic (fixed NumPy seed) so the bundled CSV/Parquet
files are reproducible. It writes both ``loan_applications`` and
``repayment_history`` in CSV and Parquet form next to this script.

Run::

    python domain-packs/consumer-credit/sample_data/gen_sample.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.csv as pa_csv
import pyarrow.parquet as pq

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
SEED = 20260617
N_APPLICATIONS = 4000
# Roughly 55% of applications are funded and therefore get a serviced account.
FUNDING_RATE = 0.55
N_SERVICING_MONTHS = 12
START_MONTH = date(2025, 1, 1)

OUT_DIR = Path(__file__).resolve().parent

DECISIONS = np.array(["approved", "declined", "review"])
DECISION_WEIGHTS = np.array([0.55, 0.30, 0.15])


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _month_iter(start: date, count: int) -> list[date]:
    """Return ``count`` consecutive first-of-month dates beginning at ``start``."""
    out: list[date] = []
    year, month = start.year, start.month
    for _ in range(count):
        out.append(date(year, month, 1))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return out


def build_applications(rng: np.random.Generator) -> tuple[pa.Table, np.ndarray, np.ndarray]:
    """Build the ``loan_applications`` table.

    Returns the table plus the funded application indices and their requested
    amounts, so repayment history can be derived consistently.
    """
    idx = np.arange(N_APPLICATIONS)

    application_id = np.array([f"APP-{i:07d}" for i in idx])
    applicant_name = np.array([f"Test User {i}" for i in idx])
    national_id = np.array([f"SYN-{i:09d}" for i in idx])
    email = np.array([f"user{i}@example.test" for i in idx])

    # Log-normal incomes, clamped to a believable EUR band, rounded to whole euros.
    income = np.round(np.clip(rng.lognormal(mean=10.6, sigma=0.45, size=N_APPLICATIONS),
                              8_000.0, 400_000.0), 2)
    # Requested amount correlates loosely with income.
    amount = np.round(np.clip(income * rng.uniform(0.1, 0.9, size=N_APPLICATIONS),
                              500.0, 150_000.0), 2)

    decision = rng.choice(DECISIONS, size=N_APPLICATIONS, p=DECISION_WEIGHTS)

    table = pa.table(
        {
            "application_id": pa.array(application_id, type=pa.string()),
            "applicant_name": pa.array(applicant_name, type=pa.string()),
            "national_id": pa.array(national_id, type=pa.string()),
            "email": pa.array(email, type=pa.string()),
            "income": pa.array(income, type=pa.float64()),
            "amount": pa.array(amount, type=pa.float64()),
            "decision": pa.array(decision, type=pa.string()),
        }
    )

    # Funded loans: a subset of approved applications get serviced accounts.
    approved_mask = decision == "approved"
    funded_mask = approved_mask & (rng.random(N_APPLICATIONS) < FUNDING_RATE / DECISION_WEIGHTS[0])
    funded_idx = idx[funded_mask]
    funded_amounts = amount[funded_mask]
    return table, funded_idx, funded_amounts


def build_repayment_history(
    rng: np.random.Generator, funded_idx: np.ndarray, funded_amounts: np.ndarray
) -> pa.Table:
    """Derive monthly servicing snapshots for each funded account."""
    months = _month_iter(START_MONTH, N_SERVICING_MONTHS)

    account_ids: list[str] = []
    month_vals: list[date] = []
    balances: list[float] = []
    dpd_vals: list[int] = []

    for app_i, principal in zip(funded_idx, funded_amounts):
        account_id = f"ACC-{int(app_i):07d}"
        # Each account amortises a fixed share of principal per month, plus noise.
        monthly_paydown = principal / (N_SERVICING_MONTHS + rng.integers(0, 6))
        balance = float(principal)
        # A minority of accounts are chronically delinquent.
        delinquency_prone = rng.random() < 0.18
        running_dpd = 0
        for m in months:
            balance = max(0.0, balance - monthly_paydown * rng.uniform(0.6, 1.1))
            if delinquency_prone and rng.random() < 0.45:
                running_dpd = min(180, running_dpd + int(rng.integers(15, 45)))
            else:
                running_dpd = max(0, running_dpd - int(rng.integers(0, 30)))

            account_ids.append(account_id)
            month_vals.append(m)
            balances.append(round(balance, 2))
            dpd_vals.append(int(running_dpd))

    return pa.table(
        {
            "account_id": pa.array(account_ids, type=pa.string()),
            "month": pa.array(month_vals, type=pa.date32()),
            "balance": pa.array(balances, type=pa.float64()),
            "days_past_due": pa.array(dpd_vals, type=pa.int32()),
        }
    )


# --------------------------------------------------------------------------- #
# IO
# --------------------------------------------------------------------------- #
def _write(table: pa.Table, stem: str) -> tuple[Path, Path]:
    csv_path = OUT_DIR / f"{stem}.csv"
    parquet_path = OUT_DIR / f"{stem}.parquet"
    pa_csv.write_csv(table, csv_path)
    pq.write_table(table, parquet_path)
    return csv_path, parquet_path


def main() -> None:
    rng = np.random.default_rng(SEED)

    applications, funded_idx, funded_amounts = build_applications(rng)
    repayment = build_repayment_history(rng, funded_idx, funded_amounts)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app_csv, app_pq = _write(applications, "loan_applications")
    rep_csv, rep_pq = _write(repayment, "repayment_history")

    print(f"loan_applications : {applications.num_rows:>6} rows -> {app_csv.name}, {app_pq.name}")
    print(f"repayment_history : {repayment.num_rows:>6} rows -> {rep_csv.name}, {rep_pq.name}")
    print(f"funded accounts   : {len(funded_idx):>6}")
    print("All identifiers are synthetic (Test User / SYN- / @example.test).")


if __name__ == "__main__":
    main()
