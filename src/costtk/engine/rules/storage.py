"""Storage & logging retention rule — S3 lifecycle + CloudWatch retention.

Two sub-cases, both gated on present signals only:
1. S3 buckets missing lifecycle rules with old last-access -> move to cheaper tier.
2. CloudWatch log groups with no retention policy (never-expire) -> set retention.
"""

from __future__ import annotations

from ...models import ActionType, Effort, Recommendation, Resource, ResourceType, Risk

S3_COLD_SAVING = 0.60  # Infrequent Access ~60% cheaper storage
COLD_AGE_DAYS = 180
CW_RETENTION_SAVING = 0.30  # trims redundant logs


def _s3_one(res: Resource, idx: int) -> Recommendation | None:
    attrs = res.attributes
    if attrs.get("lifecycle_rule"):
        return None  # already has a lifecycle policy
    if attrs.get("last_access_days", 0) < COLD_AGE_DAYS:
        return None
    current = res.current_monthly_cost
    if current <= 0:
        return None
    gross = round(current * S3_COLD_SAVING, 2)
    return Recommendation(
        id=f"s3-{idx:06d}",
        account_id=res.account_id,
        region=res.region,
        resource_id=res.resource_id,
        resource_type=ResourceType.S3,
        action=ActionType.STORAGE_RETENTION,
        current_monthly_cost=current,
        projected_monthly_cost=round(current - gross, 2),
        gross_savings=gross,
        effort=Effort.LOW,
        risk=Risk.LOW,
        restart_required=False,
        rollback_possible=True,
        evidence_confidence=0.8,
        notes=f"No lifecycle rule; last access {attrs['last_access_days']}d ago -> "
        "move to Infrequent Access.",
    )


def _cw_one(res: Resource, idx: int) -> Recommendation | None:
    attrs = res.attributes
    if attrs.get("retention_days", 0) != 3650:  # 3650 = "never expire"
        return None
    current = res.current_monthly_cost
    if current <= 0:
        return None
    gross = round(current * CW_RETENTION_SAVING, 2)
    return Recommendation(
        id=f"cw-{idx:06d}",
        account_id=res.account_id,
        region=res.region,
        resource_id=res.resource_id,
        resource_type=ResourceType.CLOUDWATCH,
        action=ActionType.STORAGE_RETENTION,
        current_monthly_cost=current,
        projected_monthly_cost=round(current - gross, 2),
        gross_savings=gross,
        effort=Effort.LOW,
        risk=Risk.LOW,
        restart_required=False,
        rollback_possible=True,
        evidence_confidence=0.8,
        notes="No log retention policy (never-expire); set a bounded retention.",
    )


def storage_retention(resources: list[Resource]) -> list[Recommendation]:
    out: list[Recommendation] = []
    idx = 0
    for res in resources:
        if res.resource_type == ResourceType.S3:
            rec = _s3_one(res, idx)
        elif res.resource_type == ResourceType.CLOUDWATCH:
            rec = _cw_one(res, idx)
        else:
            rec = None
        idx += 1
        if rec:
            out.append(rec)
    return out
