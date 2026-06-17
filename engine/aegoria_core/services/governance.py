"""``default`` governance service — the trust fabric of the lite engine.

Privacy and sovereignty are DEFAULT-ON here, not opt-in:

* :meth:`classify` runs regex/heuristic PII/PHI detection over field names and a
  data sample, tags fields and raises dataset sensitivity.
* :meth:`authorize` evaluates ABAC/RBAC over loaded domain-pack policies and the
  privacy defaults: a non-owner reading PII gets a ``mask`` obligation; an
  aggregate over sensitive data gets ``differential_privacy``; residency is
  enforced when the dataset's jurisdiction requires it.
* :meth:`apply_obligations` enforces mask / aggregate_only / differential_privacy
  on the Arrow result before it leaves the engine, tracking the DP budget.
* :meth:`evaluate_quality` runs the declared not_null/unique/range/regex/enum/
  freshness rules.
* :meth:`federated_round` is a stub coordinator that aggregates per-node model
  weights WITHOUT moving raw data — the privacy-preserving learning seam.
"""

from __future__ import annotations

import ast
import hashlib
import re
import threading
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import structlog

from ..contracts.domain_pack import AccessPolicySpec
from ..contracts.models import (
    AccessDecision,
    AccessRequest,
    Action,
    DatasetMetadata,
    DatasetRef,
    Obligation,
    PrivacyBudget,
    QualityReport,
    QualityRule,
    RuleResult,
    Sensitivity,
    TableSchema,
)
from ..engine import EngineContext
from ..registry import service

log = structlog.get_logger("aegoria.service.governance")

# --------------------------------------------------------------------------- #
# PII / PHI heuristics. Name hints catch columns; value regexes catch content.
# --------------------------------------------------------------------------- #
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s().-]{7,}\d)(?!\d)")
_NATIONAL_ID_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")  # US SSN-style
_NAME_HINTS = ("name", "first_name", "last_name", "full_name", "surname", "given_name")
_PII_NAME_HINTS = ("email", "phone", "ssn", "national_id", "passport", "address", "dob", "birth")
_PHI_NAME_HINTS = ("diagnosis", "icd", "mrn", "patient", "medical", "health", "treatment")


class DefaultGovernance:
    """ABAC/RBAC + PII classification + obligation enforcement + DP accounting."""

    def __init__(self, ctx: EngineContext) -> None:
        self._ctx = ctx
        self._lock = threading.RLock()
        # domain -> [policies]
        self._policies: dict[str, list[AccessPolicySpec]] = {}
        # (subject, ref.id) -> spent epsilon
        self._budgets: dict[tuple[str, str], float] = {}

    # ------------------------------------------------------------------ #
    # Policy loading (called by engine.load_domain_pack).
    # ------------------------------------------------------------------ #
    def load_policies(self, domain: str, policies: list[AccessPolicySpec]) -> None:
        with self._lock:
            self._policies[domain] = list(policies)
        log.debug("load_policies", domain=domain, count=len(policies))

    # ------------------------------------------------------------------ #
    # Classification.
    # ------------------------------------------------------------------ #
    def classify(self, meta: DatasetMetadata, sample: Optional[pa.Table] = None) -> DatasetMetadata:
        updated = meta.model_copy(deep=True)
        schema = updated.schema_
        dataset_sensitivity = updated.modality  # placeholder; we track via fields below
        max_sensitivity = Sensitivity.PUBLIC
        for field in schema.fields:
            lname = field.name.lower()
            detected = field.sensitivity
            is_pii = field.pii
            # Name-based hints.
            if any(h in lname for h in _PHI_NAME_HINTS):
                detected, is_pii = Sensitivity.PHI, True
            elif any(h in lname for h in _PII_NAME_HINTS) or any(h in lname for h in _NAME_HINTS):
                detected, is_pii = Sensitivity.PII, True
            # Value-based detection on a sample.
            if sample is not None and field.name in sample.column_names:
                kind = self._scan_values(sample.column(field.name))
                if kind == "phi":
                    detected, is_pii = Sensitivity.PHI, True
                elif kind == "pii":
                    detected, is_pii = Sensitivity.PII, True
            field.pii = is_pii
            if detected != Sensitivity.PUBLIC:
                field.sensitivity = detected
            max_sensitivity = self._max_sensitivity(max_sensitivity, field.sensitivity)
        # Raise dataset sensitivity into tags for discoverability + reuse signal.
        if max_sensitivity in (Sensitivity.PII, Sensitivity.PHI) and "sensitive" not in updated.tags:
            updated.tags = [*updated.tags, "sensitive"]
        updated.updated_at = datetime.now(timezone.utc)
        log.debug("classify", ref=updated.ref.id, max_sensitivity=max_sensitivity.value)
        _ = dataset_sensitivity  # silence linters; modality untouched
        return updated

    @staticmethod
    def _scan_values(column: pa.ChunkedArray) -> Optional[str]:
        """Sniff a column's string values for email/phone/national-id/health markers."""
        try:
            values = column.cast(pa.string()).to_pylist()
        except Exception:
            return None
        hits = 0
        checked = 0
        for v in values:
            if v is None:
                continue
            checked += 1
            if checked > 200:
                break
            s = str(v)
            if _EMAIL_RE.search(s) or _NATIONAL_ID_RE.search(s) or _PHONE_RE.search(s):
                hits += 1
        if checked and hits / checked >= 0.3:
            return "pii"
        return None

    @staticmethod
    def _max_sensitivity(a: Sensitivity, b: Sensitivity) -> Sensitivity:
        order = {
            Sensitivity.PUBLIC: 0,
            Sensitivity.INTERNAL: 1,
            Sensitivity.CONFIDENTIAL: 2,
            Sensitivity.FINANCIAL: 3,
            Sensitivity.PII: 4,
            Sensitivity.PHI: 5,
            Sensitivity.RESTRICTED: 6,
        }
        return a if order[a] >= order[b] else b

    # ------------------------------------------------------------------ #
    # Authorization (ABAC/RBAC + privacy/sovereignty defaults).
    # ------------------------------------------------------------------ #
    def authorize(self, request: AccessRequest, meta: DatasetMetadata) -> AccessDecision:
        principal = request.principal
        obligations: list[Obligation] = []
        policy_id: Optional[str] = None

        # 0. Super-admin / break-glass — the apex role. Unrestricted access with NO
        # obligations (no masking, DP, residency or policy denial). Use sparingly;
        # every such access is still recorded by the caller's audit log.
        if _has_role(principal, _SUPERADMIN_ROLES):
            return AccessDecision(
                allow=True,
                reason="super-admin: unrestricted access (break-glass)",
                policy_id="builtin:superadmin",
            )

        # 1. Residency / sovereignty — DEFAULT ON when the jurisdiction requires it.
        juris = meta.jurisdiction
        residency_on = juris.residency_required or self._ctx.config.privacy.residency_enforced
        if juris.residency_required:
            principal_region = str(principal.attributes.get("region", principal.jurisdiction))
            if principal_region not in (juris.code, juris.region, "GLOBAL") and principal.jurisdiction != juris.code:
                return AccessDecision(
                    allow=False,
                    reason=f"residency: data is bound to {juris.code}, principal in {principal.jurisdiction}",
                    policy_id="builtin:residency",
                )
            obligations.append(Obligation(kind="residency", params={"code": juris.code}))

        # 2. Domain-pack policy evaluation (explicit allow/deny).
        decision_from_policy = self._evaluate_policies(request, meta)
        if decision_from_policy is not None:
            allowed, policy_id, policy_obls = decision_from_policy
            if not allowed:
                return AccessDecision(allow=False, reason=f"denied by policy {policy_id}", policy_id=policy_id)
            obligations.extend(policy_obls)
        else:
            # 3. Default RBAC: deny writes/admin/export to non-owners w/o role.
            if request.action in (Action.WRITE, Action.ADMIN):
                if principal.subject != meta.owner and not _has_role(principal, {"admin", "owner", "writer"}):
                    return AccessDecision(
                        allow=False,
                        reason=f"action {request.action.value} requires owner/admin role",
                        policy_id="builtin:rbac",
                    )

        is_owner = principal.subject == meta.owner or _has_role(principal, {"admin", "owner"})
        has_pii = bool(meta.schema_.pii_fields)

        # 3b. Raw row-level READ of PII by a non-owner is denied outright. Sensitive
        # data may only be reached through aggregates (with differential privacy) or
        # explicitly de-identified/masked queries — never as raw rows.
        if request.action == Action.READ and has_pii and not is_owner:
            return AccessDecision(
                allow=False,
                reason="raw read of PII is not permitted for non-owners; use an aggregate or de-identified query",
                policy_id="builtin:no-raw-pii-read",
            )

        # 4. Export of PII is denied by default (sovereignty/privacy).
        if (
            request.action == Action.EXPORT
            and has_pii
            and not is_owner
            and self._ctx.config.privacy.deny_export_of_pii
        ):
            return AccessDecision(
                allow=False,
                reason="export of PII denied by default privacy policy",
                policy_id="builtin:deny-pii-export",
            )

        # 5. Privacy DEFAULT-ON obligations.
        if has_pii and not is_owner:
            obligations.append(
                Obligation(kind="mask", params={"fields": meta.schema_.pii_fields, "strategy": "hash"})
            )
        if (
            request.action in (Action.AGGREGATE, Action.QUERY, Action.SAMPLE)
            and self._is_sensitive(meta)
            and not is_owner
        ):
            if request.action == Action.SAMPLE:
                obligations.append(Obligation(kind="aggregate_only", params={}))
            if self._ctx.config.privacy.differential_privacy:
                obligations.append(
                    Obligation(
                        kind="differential_privacy",
                        params={
                            "epsilon": self._ctx.config.privacy.default_epsilon,
                            "delta": self._ctx.config.privacy.default_delta,
                        },
                    )
                )

        if residency_on and not any(o.kind == "residency" for o in obligations):
            obligations.append(Obligation(kind="residency", params={"code": juris.code}))

        obligations = _dedupe_obligations(obligations)
        return AccessDecision(
            allow=True,
            reason="authorized" + (" with obligations" if obligations else ""),
            obligations=obligations,
            policy_id=policy_id,
        )

    def _evaluate_policies(
        self, request: AccessRequest, meta: DatasetMetadata
    ) -> Optional[tuple[bool, str, list[Obligation]]]:
        policies = self._policies.get(request.dataset.domain, [])
        if not policies:
            return None
        action = request.action.value
        principal = request.principal
        matched: Optional[tuple[bool, str, list[Obligation]]] = None
        for pol in policies:
            if pol.datasets and not _glob_match(meta.ref.name, pol.datasets):
                continue
            if pol.actions and action not in pol.actions and "*" not in pol.actions:
                continue
            if pol.roles and "*" not in pol.roles and not (set(pol.roles) & set(principal.roles)):
                continue
            # A guard condition decides whether this policy APPLIES to the request.
            # (Fixes the previous behavior where a deny rule fired unconditionally.)
            if pol.condition:
                try:
                    if not _eval_condition(pol.condition, request, meta):
                        continue
                except Exception as exc:  # malformed/unevaluable guard -> policy does not apply
                    log.warning(
                        "policy_condition_uneval", policy=pol.id, condition=pol.condition, error=str(exc)
                    )
                    continue
            obls = [Obligation(kind=o["kind"], params=o.get("params", {})) for o in pol.obligations]
            if pol.effect == "deny":
                return (False, pol.id, [])
            matched = (True, pol.id, obls)
        return matched

    def _is_sensitive(self, meta: DatasetMetadata) -> bool:
        sensitive = {Sensitivity.PII, Sensitivity.PHI, Sensitivity.FINANCIAL, Sensitivity.RESTRICTED}
        return any(f.sensitivity in sensitive or f.pii for f in meta.schema_.fields)

    # ------------------------------------------------------------------ #
    # Obligation enforcement on query output.
    # ------------------------------------------------------------------ #
    def apply_obligations(
        self, data: pa.Table, obligations: list[Obligation], *, schema: TableSchema
    ) -> pa.Table:
        result = data
        for obl in obligations:
            if obl.kind == "mask":
                result = self._apply_mask(result, obl, schema)
            elif obl.kind == "aggregate_only":
                self._enforce_aggregate_only(result)
            elif obl.kind == "differential_privacy":
                result = self._apply_dp(result, obl)
            # residency / watermark are placement/provenance obligations: no-op here.
        return result

    @staticmethod
    def _apply_mask(data: pa.Table, obl: Obligation, schema: TableSchema) -> pa.Table:
        fields = set(obl.params.get("fields") or schema.pii_fields)
        strategy = obl.params.get("strategy", "hash")
        if not fields:
            return data
        cols = []
        names = data.column_names
        for name in names:
            col = data.column(name)
            if name in fields:
                if strategy == "null":
                    col = pa.nulls(data.num_rows, type=col.type)
                else:  # hash
                    hashed = [
                        None if v is None else hashlib.sha256(str(v).encode()).hexdigest()[:16]
                        for v in col.to_pylist()
                    ]
                    col = pa.array(hashed, type=pa.string())
            cols.append(col)
        return pa.table(cols, names=names)

    @staticmethod
    def _enforce_aggregate_only(data: pa.Table) -> None:
        # Row-level output on an aggregate_only dataset is a policy violation.
        # Heuristic: more than one output row that is not itself an aggregate.
        if data.num_rows > 1:
            from ..errors import AccessDenied

            raise AccessDenied("aggregate_only: row-level output is not permitted")

    def _apply_dp(self, data: pa.Table, obl: Obligation) -> pa.Table:
        epsilon = float(obl.params.get("epsilon", self._ctx.config.privacy.default_epsilon))
        sensitivity = float(obl.params.get("sensitivity", 1.0))
        rng = np.random.default_rng()
        cols = []
        names = data.column_names
        for name in names:
            col = data.column(name)
            if pa.types.is_floating(col.type) or pa.types.is_integer(col.type):
                vals = np.array(col.to_pylist(), dtype="float64")
                scale = sensitivity / max(epsilon, 1e-9)
                noise = rng.laplace(0.0, scale, size=vals.shape)
                noisy = vals + noise
                if pa.types.is_integer(col.type):
                    col = pa.array(np.rint(noisy).astype("int64"))
                else:
                    col = pa.array(noisy)
            cols.append(col)
        return pa.table(cols, names=names)

    # ------------------------------------------------------------------ #
    # Differential-privacy budget accounting.
    # ------------------------------------------------------------------ #
    def budget(self, subject: str, ref: DatasetRef) -> PrivacyBudget:
        with self._lock:
            spent = self._budgets.get((subject, ref.id), 0.0)
        return PrivacyBudget(
            epsilon=self._ctx.config.privacy.default_epsilon,
            delta=self._ctx.config.privacy.default_delta,
            spent=spent,
        )

    def spend_budget(self, subject: str, ref: DatasetRef, epsilon: float) -> PrivacyBudget:
        with self._lock:
            key = (subject, ref.id)
            self._budgets[key] = self._budgets.get(key, 0.0) + epsilon
        return self.budget(subject, ref)

    # ------------------------------------------------------------------ #
    # Quality evaluation.
    # ------------------------------------------------------------------ #
    def evaluate_quality(
        self, meta: DatasetMetadata, data: pa.Table, rules: list[QualityRule]
    ) -> QualityReport:
        results: list[RuleResult] = []
        for rule in rules:
            results.append(self._eval_rule(rule, data))
        report = QualityReport(dataset=meta.ref, results=results)
        log.debug("evaluate_quality", ref=meta.ref.id, score=report.score)
        return report

    def _eval_rule(self, rule: QualityRule, data: pa.Table) -> RuleResult:
        try:
            if rule.kind == "not_null":
                return self._rule_not_null(rule, data)
            if rule.kind == "unique":
                return self._rule_unique(rule, data)
            if rule.kind == "range":
                return self._rule_range(rule, data)
            if rule.kind == "regex":
                return self._rule_regex(rule, data)
            if rule.kind == "enum":
                return self._rule_enum(rule, data)
            if rule.kind == "freshness":
                return self._rule_freshness(rule, data)
        except Exception as exc:  # pragma: no cover - defensive
            return RuleResult(rule_id=rule.id, passed=False, message=f"error: {exc}")
        return RuleResult(rule_id=rule.id, passed=True, message=f"unsupported kind {rule.kind!r}; skipped")

    @staticmethod
    def _col(data: pa.Table, name: Optional[str]) -> pa.ChunkedArray:
        if not name or name not in data.column_names:
            raise ValueError(f"rule field {name!r} not in table")
        return data.column(name)

    def _rule_not_null(self, rule: QualityRule, data: pa.Table) -> RuleResult:
        col = self._col(data, rule.field)
        nulls = col.null_count
        return RuleResult(rule_id=rule.id, passed=nulls == 0, violations=nulls, sampled=len(col))

    def _rule_unique(self, rule: QualityRule, data: pa.Table) -> RuleResult:
        col = self._col(data, rule.field)
        n = len(col)
        distinct = pc.count_distinct(col).as_py()
        dups = n - distinct
        return RuleResult(rule_id=rule.id, passed=dups == 0, violations=dups, sampled=n)

    def _rule_range(self, rule: QualityRule, data: pa.Table) -> RuleResult:
        col = self._col(data, rule.field)
        lo = rule.params.get("min")
        hi = rule.params.get("max")
        vals = col.to_pylist()
        viol = 0
        for v in vals:
            if v is None:
                continue
            if lo is not None and v < lo:
                viol += 1
            elif hi is not None and v > hi:
                viol += 1
        return RuleResult(rule_id=rule.id, passed=viol == 0, violations=viol, sampled=len(vals))

    def _rule_regex(self, rule: QualityRule, data: pa.Table) -> RuleResult:
        col = self._col(data, rule.field)
        pattern = re.compile(rule.params["pattern"])
        vals = col.cast(pa.string()).to_pylist()
        viol = sum(1 for v in vals if v is not None and not pattern.fullmatch(v))
        return RuleResult(rule_id=rule.id, passed=viol == 0, violations=viol, sampled=len(vals))

    def _rule_enum(self, rule: QualityRule, data: pa.Table) -> RuleResult:
        col = self._col(data, rule.field)
        allowed = set(rule.params.get("values", []))
        vals = col.to_pylist()
        viol = sum(1 for v in vals if v is not None and v not in allowed)
        return RuleResult(rule_id=rule.id, passed=viol == 0, violations=viol, sampled=len(vals))

    def _rule_freshness(self, rule: QualityRule, data: pa.Table) -> RuleResult:
        col = self._col(data, rule.field)
        max_age_s = float(rule.params.get("max_age_seconds", 86400))
        now = datetime.now(timezone.utc)
        viol = 0
        sampled = 0
        for v in col.to_pylist():
            if v is None:
                continue
            sampled += 1
            ts = v if isinstance(v, datetime) else datetime.fromisoformat(str(v))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if (now - ts).total_seconds() > max_age_s:
                viol += 1
        return RuleResult(rule_id=rule.id, passed=viol == 0, violations=viol, sampled=sampled)

    # ------------------------------------------------------------------ #
    # Federated learning coordinator (privacy-preserving: no raw data moves).
    # ------------------------------------------------------------------ #
    def federated_round(self, domain: str, model_id: str, updates: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
        """Aggregate per-node model weight updates WITHOUT moving raw data.

        Each participating node trains locally and submits only weight deltas +
        sample counts. The coordinator computes a sample-weighted federated
        average (FedAvg). No row-level data ever crosses a node boundary, which
        is the privacy guarantee that lets sovereign datasets contribute to a
        shared model. ``updates`` is a list of ``{weights: {k: float}, samples:
        int}`` dicts; absent updates yield an empty aggregate descriptor.
        """
        updates = updates or []
        total_samples = sum(int(u.get("samples", 0)) for u in updates) or 1
        aggregated: dict[str, float] = {}
        for u in updates:
            w = u.get("samples", 0) / total_samples
            for k, val in (u.get("weights") or {}).items():
                aggregated[k] = aggregated.get(k, 0.0) + w * float(val)
        return {
            "domain": domain,
            "model_id": model_id,
            "participants": len(updates),
            "total_samples": total_samples,
            "aggregated_weights": aggregated,
            "raw_data_moved": False,
            "strategy": "fedavg",
        }


def _dedupe_obligations(obligations: list[Obligation]) -> list[Obligation]:
    """Collapse duplicate obligations so enforcement isn't applied twice.

    Privacy stays strict: when differential privacy is attached more than once
    (e.g. a pack policy plus the default-on rule), keep the STRONGEST guarantee
    (smallest epsilon). Mask field-sets are unioned.
    """
    out: dict[str, Obligation] = {}
    for obl in obligations:
        existing = out.get(obl.kind)
        if existing is None:
            out[obl.kind] = obl
            continue
        if obl.kind == "differential_privacy":
            if float(obl.params.get("epsilon", 1e9)) < float(existing.params.get("epsilon", 1e9)):
                out[obl.kind] = obl
        elif obl.kind == "mask":
            fields = sorted(set(existing.params.get("fields", [])) | set(obl.params.get("fields", [])))
            out[obl.kind] = Obligation(kind="mask", params={**existing.params, "fields": fields})
        # other kinds (aggregate_only / residency / watermark) are idempotent — keep first.
    return list(out.values())


# The apex RBAC roles: full, unrestricted, break-glass access.
_SUPERADMIN_ROLES = {"superadmin", "root"}


def _has_role(principal: Any, roles: set[str]) -> bool:
    return bool(set(principal.roles) & roles)


def _glob_match(name: str, patterns: list[str]) -> bool:
    from fnmatch import fnmatch

    return any(fnmatch(name, pat) for pat in patterns)


class _NS:
    """Read-only attribute/dict view used as the condition-evaluation namespace.

    Lets a CEL-like policy condition use either ``principal.jurisdiction`` (object
    attribute) or ``principal.attributes.purpose`` (nested dict key) uniformly.
    """

    __slots__ = ("_d",)

    def __init__(self, data: dict[str, Any]) -> None:
        self._d = data

    def __getattr__(self, key: str) -> Any:
        val = self._d.get(key)
        return _NS(val) if isinstance(val, dict) else val


# AST node/operator allow-lists — we never call eval(); we walk a parsed tree.
_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.UnaryOp, ast.Compare, ast.Name, ast.Load,
    ast.Attribute, ast.Constant, ast.List, ast.Tuple, ast.Set,
    ast.And, ast.Or, ast.Not,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
)


def _condition_namespace(request: AccessRequest, meta: DatasetMetadata) -> dict[str, Any]:
    p = request.principal
    clearance = getattr(p.clearance, "value", str(p.clearance))
    principal = {
        "subject": p.subject,
        "roles": list(p.roles),
        "jurisdiction": p.jurisdiction,
        "clearance": clearance,
        "attributes": dict(p.attributes),
        "org": p.attributes.get("org"),
        "region": p.attributes.get("region", p.jurisdiction),
        "purpose": p.attributes.get("purpose"),
    }
    resource = {
        "owner": meta.owner,
        "domain": meta.ref.domain,
        "name": meta.ref.name,
        "jurisdiction": meta.jurisdiction.code,
        "residency_required": meta.jurisdiction.residency_required,
    }
    compute = {"region": p.attributes.get("region", p.jurisdiction)}
    return {
        "principal": _NS(principal),
        "resource": _NS(resource),
        "compute": _NS(compute),
        "true": True,
        "false": False,
        "null": None,
    }


def _eval_node(node: ast.AST, ns: dict[str, Any]) -> Any:
    if not isinstance(node, _ALLOWED_NODES):
        raise ValueError(f"disallowed expression node: {type(node).__name__}")
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, ns)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in ns:
            raise NameError(node.id)
        return ns[node.id]
    if isinstance(node, ast.Attribute):
        return getattr(_eval_node(node.value, ns), node.attr)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [_eval_node(e, ns) for e in node.elts]
    if isinstance(node, ast.BoolOp):
        vals = [_eval_node(v, ns) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.UnaryOp):  # Not
        return not _eval_node(node.operand, ns)
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, ns)
        for op, comp in zip(node.ops, node.comparators):
            right = _eval_node(comp, ns)
            if not _apply_cmp(op, left, right):
                return False
            left = right
        return True
    raise ValueError(f"unhandled node: {type(node).__name__}")


def _apply_cmp(op: ast.cmpop, left: Any, right: Any) -> bool:
    if isinstance(op, ast.Eq):
        return left == right
    if isinstance(op, ast.NotEq):
        return left != right
    if isinstance(op, ast.In):
        return left in right
    if isinstance(op, ast.NotIn):
        return left not in right
    # Ordered comparisons: guard against None to avoid TypeErrors.
    if left is None or right is None:
        return False
    if isinstance(op, ast.Lt):
        return left < right
    if isinstance(op, ast.LtE):
        return left <= right
    if isinstance(op, ast.Gt):
        return left > right
    if isinstance(op, ast.GtE):
        return left >= right
    raise ValueError(f"unsupported comparator: {type(op).__name__}")


def _eval_condition(condition: str, request: AccessRequest, meta: DatasetMetadata) -> bool:
    """Safely evaluate a CEL-like policy guard. Returns whether the policy APPLIES.

    No ``eval``/``exec`` — only a whitelisted AST is walked. Raises on anything it
    cannot evaluate so the caller can decide how to treat an unparseable guard.
    """
    tree = ast.parse(condition.strip(), mode="eval")
    return bool(_eval_node(tree, _condition_namespace(request, meta)))


@service("governance", "default")
def make_default_governance(*, ctx: EngineContext) -> DefaultGovernance:
    """Factory the engine invokes to build the default governance service."""
    return DefaultGovernance(ctx)
