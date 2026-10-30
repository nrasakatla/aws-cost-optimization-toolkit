"""Savings Plans rule — recommend Compute Savings Plans for steady-state usage.

A Savings Plan is worthwhile when a workload's usage is committed/steady (high
utilization, always-on). It yields a percentage discount over on-demand. Only
recommended where the resource runs 24/7 and utilization justifies commitment.
"""

from __future__ import annotations

from ...models import ActionType, Effort, Recommendation, Resource, ResourceType, Risk

SP_DISCOUNT = 0.28  # ~28% savings vs on-demand for 1yr no-upfront Compute SP
MIN_COMMIT_PROOF = 0.60  # workload must be >60% steady to justify commitment


def _sp_one(res: Resource, idx: int) -> Recommendation | None:
    if res.resource_type != ResourceType.EC2:
        return None
    attrs = res.attributes
    cpu = attrs.get("cpu_util")
    if cpu is None:
        return None
    running = attrs.get("running_hours_per_month", 0.0)
    if running < 700:  # not effectively always-on
        return None
    if cpu < MIN_COMMIT_PROOF:
        return None  # not steady enough to commit

    current = res.current_monthly_cost
    gross = round(current * SP_DISCOUNT, 2)
    if gross <= 0:
        return None
    return Recommendation(
        id=f"sp-{idx:06d}",
        account_id=res.account_id,
        region=res.region,
        resource_id=res.resource_id,
        resource_type=ResourceType.EC2,
        action=ActionType.SAVINGS_PLANS,
        current_monthly_cost=current,
        projected_monthly_cost=round(current - gross, 2),
        gross_savings=gross,
        effort=Effort.VERY_LOW,
        risk=Risk.LOW,
        restart_required=False,
        rollback_possible=True,
        evidence_confidence=0.85,
        notes=f"Steady {cpu:.0%} util, always-on: 1yr no-upfront Compute SP "
        f"at {SP_DISCOUNT:.0%} discount.",
    )


def savings_plans(resources: list[Resource]) -> list[Recommendation]:
    out: list[Recommendation] = []
    idx = 0
    for res in resources:
        rec = _sp_one(res, idx)
        idx += 1
        if rec:
            out.append(rec)
    return out
