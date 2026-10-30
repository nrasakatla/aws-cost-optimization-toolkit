"""Reserved Instances rule — recommend RDS/ElastiCache/OpenSearch RIs.

Databases and other stateful services that are always-on are strong RI
candidates. Applies a deeper discount than SPs (longer commitment, specific
resource). Only for 24/7 steady-state production resources.
"""

from __future__ import annotations

from ...models import ActionType, Effort, Recommendation, Resource, ResourceType, Risk

RI_DISCOUNT = 0.42  # ~42% discount for 1yr no-upfront RIs
RI_TYPES = {ResourceType.RDS, ResourceType.ELASTICACHE, ResourceType.OPENSEARCH}
MIN_RUN_PROOF = 700.0


def _ri_one(res: Resource, idx: int) -> Recommendation | None:
    if res.resource_type not in RI_TYPES:
        return None
    if res.environment != "prod":
        return None  # don't reserve non-prod
    running = res.attributes.get("running_hours_per_month", 0.0)
    if running < MIN_RUN_PROOF:
        return None

    current = res.current_monthly_cost
    if current <= 0:
        return None
    gross = round(current * RI_DISCOUNT, 2)
    return Recommendation(
        id=f"ri-{idx:06d}",
        account_id=res.account_id,
        region=res.region,
        resource_id=res.resource_id,
        resource_type=res.resource_type,
        action=ActionType.RESERVED_INSTANCES,
        current_monthly_cost=current,
        projected_monthly_cost=round(current - gross, 2),
        gross_savings=gross,
        effort=Effort.VERY_LOW,
        risk=Risk.LOW,
        restart_required=False,
        rollback_possible=True,
        evidence_confidence=0.85,
        notes=f"Always-on prod {res.resource_type.value}: 1yr no-upfront RI "
        f"at {RI_DISCOUNT:.0%} discount.",
    )


def reserved_instances(resources: list[Resource]) -> list[Recommendation]:
    out: list[Recommendation] = []
    idx = 0
    for res in resources:
        rec = _ri_one(res, idx)
        idx += 1
        if rec:
            out.append(rec)
    return out
