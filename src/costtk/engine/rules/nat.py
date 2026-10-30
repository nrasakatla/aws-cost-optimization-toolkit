"""NAT Gateway optimization rule — reduce data-transfer cost via VPC endpoints.

NAT gateways incur both an hourly charge and per-GB data processing charges.
Traffic that could flow through VPC gateway endpoints (S3, DynamoDB) instead of
the NAT gateway avoids that per-GB charge. The saving is only the *data* fee on
traffic already eligible for endpoint routing.
"""

from __future__ import annotations

from ...models import ActionType, Effort, Recommendation, Resource, ResourceType, Risk
from ...providers.sample import ASSUMPTIONS

ENDPOINT_ELIGIBLE_MIN = 0.05  # only worth it if >5% of traffic is endpoint-eligible


def _nat_one(res: Resource, idx: int) -> Recommendation | None:
    if res.resource_type != ResourceType.NAT:
        return None
    attrs = res.attributes
    data_gb = attrs.get("data_gb_per_month", 0.0)
    endpoint_pct = attrs.get("traffic_through_vpc_endpoints_pct", 0.0)
    if data_gb <= 0 or endpoint_pct < ENDPOINT_ELIGIBLE_MIN:
        return None

    # Re-route the endpoint-eligible share through endpoints -> avoid NAT data fee.
    eligible_gb = data_gb * endpoint_pct
    gross = round(eligible_gb * ASSUMPTIONS.nat_data_per_gb, 2)
    if gross <= 0:
        return None
    return Recommendation(
        id=f"nat-{idx:06d}",
        account_id=res.account_id,
        region=res.region,
        resource_id=res.resource_id,
        resource_type=ResourceType.NAT,
        action=ActionType.NAT_OPTIMIZE,
        current_monthly_cost=res.current_monthly_cost,
        projected_monthly_cost=round(res.current_monthly_cost - gross, 2),
        gross_savings=gross,
        effort=Effort.MEDIUM,
        risk=Risk.LOW,
        restart_required=False,
        rollback_possible=True,
        evidence_confidence=0.75,
        notes=f"Route {endpoint_pct:.0%} of NAT egress ({eligible_gb:.0f}GB) "
        f"through VPC gateway endpoints.",
    )


def nat_optimize(resources: list[Resource]) -> list[Recommendation]:
    out: list[Recommendation] = []
    idx = 0
    for res in resources:
        rec = _nat_one(res, idx)
        idx += 1
        if rec:
            out.append(rec)
    return out
