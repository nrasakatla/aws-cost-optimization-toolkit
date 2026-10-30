"""Scheduling rule — stop non-production compute outside required hours.

Non-prod environments (staging/dev/test) that run 24/7 can be scheduled to run
only during business hours. Savings = cost avoided by scheduling downtime.
Only applies to environments meant to be ephemeral; prod is never scheduled.
"""

from __future__ import annotations

from ...models import ActionType, Effort, Recommendation, Resource, ResourceType, Risk

SCHEDULABLE_HOURS = 12.0  # run 12h/day instead of 24
HOURS_PER_DAY = 24.0
NON_PROD_ENVS = {"staging", "dev", "test"}
SCHEDULABLE_TYPES = {ResourceType.EC2, ResourceType.RDS}


def _schedule_one(res: Resource, idx: int) -> Recommendation | None:
    if res.environment not in NON_PROD_ENVS:
        return None
    if res.resource_type not in SCHEDULABLE_TYPES:
        return None
    current = res.current_monthly_cost
    if current <= 0:
        return None
    # Non-idle non-prod compute: schedule to business hours.
    # Savings = fraction of hours avoided.
    savings_fraction = (HOURS_PER_DAY - SCHEDULABLE_HOURS) / HOURS_PER_DAY
    projected = round(current * SCHEDULABLE_HOURS / HOURS_PER_DAY, 2)
    gross = round(current - projected, 2)
    return Recommendation(
        id=f"schedule-{idx:06d}",
        account_id=res.account_id,
        region=res.region,
        resource_id=res.resource_id,
        resource_type=res.resource_type,
        action=ActionType.SCHEDULE,
        current_monthly_cost=current,
        projected_monthly_cost=projected,
        gross_savings=gross,
        effort=Effort.MEDIUM,
        risk=Risk.MEDIUM,
        restart_required=False,
        rollback_possible=True,
        evidence_confidence=0.85,
        notes=f"Schedule {res.environment} workload to {SCHEDULABLE_HOURS:.0f}h/day "
        f"({savings_fraction:.0%} monthly saving).",
    )


def schedule(resources: list[Resource]) -> list[Recommendation]:
    out: list[Recommendation] = []
    idx = 0
    for res in resources:
        rec = _schedule_one(res, idx)
        idx += 1
        if rec:
            out.append(rec)
    return out
