"""EBS rule — gp2 -> gp3 upgrade and stale-snapshot cleanup.

gp3 is 20% cheaper per GB than gp2 under the pricing assumptions, with a free
IOPS baseline. Also flags unattached/stale snapshots that can be deleted.
"""

from __future__ import annotations

from ...models import ActionType, Effort, Recommendation, Resource, ResourceType, Risk
from ...providers.sample import ASSUMPTIONS


def gp3_price(size_gb: float) -> float:
    """Monthly gp3 cost for a given size under the documented assumptions."""
    return float(ASSUMPTIONS.ebs_gp3_per_gb_month) * float(size_gb)


def _ebs_one(res: Resource, idx: int) -> Recommendation | None:
    if res.resource_type != ResourceType.EBS:
        return None
    attrs = res.attributes
    current = res.current_monthly_cost

    # gp2 -> gp3 migration (20% cheaper per GB).
    if attrs.get("volume_type") == "gp2":
        size = attrs.get("size_gb", 0)
        if size:
            projected = round(gp3_price(size), 2)
            gross = round(current - projected, 2)
            if gross > 0:
                return Recommendation(
                    id=f"ebs-up-{idx:06d}",
                    account_id=res.account_id,
                    region=res.region,
                    resource_id=res.resource_id,
                    resource_type=ResourceType.EBS,
                    action=ActionType.EBS_UPGRADE,
                    current_monthly_cost=current,
                    projected_monthly_cost=projected,
                    gross_savings=gross,
                    effort=Effort.VERY_LOW,
                    risk=Risk.LOW,
                    restart_required=False,
                    rollback_possible=True,
                    evidence_confidence=0.95,
                    notes=f"gp2 -> gp3: {size}GB at 20% cheaper per-GB rate.",
                )

    # Stale snapshot cleanup.
    age = attrs.get("snapshot_age_days", 0)
    if age >= 365:
        snap_cost = round(size_or_zero(attrs) * 0.05, 2)
        if snap_cost <= 0:
            return None
        return Recommendation(
            id=f"ebs-snap-{idx:06d}",
            account_id=res.account_id,
            region=res.region,
            resource_id=res.resource_id,
            resource_type=ResourceType.EBS,
            action=ActionType.STORAGE_RETENTION,
            current_monthly_cost=current,
            projected_monthly_cost=round(current - snap_cost, 2),
            gross_savings=snap_cost,
            effort=Effort.LOW,
            risk=Risk.LOW,
            restart_required=False,
            rollback_possible=True,
            evidence_confidence=0.8,
            notes=f"Stale snapshot {age} days old; delete to recover snapshot storage.",
        )
    return None


def size_or_zero(attrs: dict) -> int:
    return int(attrs.get("size_gb", 0) or 0)


def ebs_upgrade(resources: list[Resource]) -> list[Recommendation]:
    out: list[Recommendation] = []
    idx = 0
    for res in resources:
        rec = _ebs_one(res, idx)
        idx += 1
        if rec:
            out.append(rec)
    return out
