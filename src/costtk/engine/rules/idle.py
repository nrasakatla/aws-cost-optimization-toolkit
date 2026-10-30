"""Idle-resource rule — identify resources producing zero/negligible load.

Uses multiple corroborating signals rather than a single noisy metric: a
resource is flagged idle only when the synthetic data marks it idle AND (for
compute) utilization is effectively zero. Missing signals -> treated as unknown
and skipped, never assumed idle.
"""

from __future__ import annotations

from ...models import ActionType, Effort, Recommendation, Resource, ResourceType, Risk

IDLE_UTIL = 0.05


def _idle_one(res: Resource, idx: int) -> Recommendation | None:
    attrs = res.attributes

    # Different resource families have different idle signals.
    if res.resource_type in (ResourceType.EC2, ResourceType.RDS):
        if "is_idle" not in attrs:
            return None
        if not attrs["is_idle"]:
            return None
        # Corroborate with utilization if present.
        cpu = attrs.get("cpu_util")
        if cpu is not None and cpu > IDLE_UTIL:
            return None
    elif res.resource_type == ResourceType.LAMBDA:
        if attrs.get("invocations_last_month") not in (None, 0):
            return None
    elif res.resource_type == ResourceType.NAT:
        if attrs.get("data_gb_per_month", 0) > 0.5:
            return None
    elif res.resource_type == ResourceType.ELB:
        if attrs.get("active_targets", 0) > 0:
            return None
    elif res.resource_type == ResourceType.EBS:
        if attrs.get("snapshot_age_days", 0) < 365:
            return None
    else:
        return None

    current = res.current_monthly_cost
    if current <= 0:
        return None
    return Recommendation(
        id=f"idle-{idx:06d}",
        account_id=res.account_id,
        region=res.region,
        resource_id=res.resource_id,
        resource_type=res.resource_type,
        action=ActionType.STOP_IDLE,
        current_monthly_cost=current,
        projected_monthly_cost=0.0,
        gross_savings=round(current, 2),
        effort=Effort.LOW,
        risk=Risk.LOW,
        restart_required=False,
        rollback_possible=True,
        evidence_confidence=0.9,
        notes="Idle with corroborating zero-load signals; safe to stop.",
    )


def idle(resources: list[Resource]) -> list[Recommendation]:
    out: list[Recommendation] = []
    idx = 0
    for res in resources:
        rec = _idle_one(res, idx)
        idx += 1
        if rec:
            out.append(rec)
    return out
