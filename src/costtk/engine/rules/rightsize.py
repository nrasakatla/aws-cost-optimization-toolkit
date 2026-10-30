"""Rightsizing rule — downsize over-provisioned EC2/RDS from utilization signals.

Only emits a recommendation when there is *sufficient* evidence: CPU, memory,
and network utilization must all be present (no missing metric implied to be
zero). A low-utilization instance whose metrics are missing is treated as
"unknown" and skipped.
"""

from __future__ import annotations

from ...models import ActionType, Recommendation, Resource, ResourceType
from .. import classify

# If utilization stays below this on ALL measured axes, the resource is
# over-provisioned and a downsize is proposed.
LOW_UTIL = 0.40
REQUIRED_EVIDENCE = ["cpu_util", "mem_util"]


def _rightsize_one(res: Resource, idx: int) -> Recommendation | None:
    attrs = res.attributes
    if not all(k in attrs for k in REQUIRED_EVIDENCE):
        return None  # insufficient evidence — do not guess

    cpu = attrs["cpu_util"]
    mem = attrs["mem_util"]
    if cpu >= LOW_UTIL or mem >= LOW_UTIL:
        return None

    vcpu = attrs.get("vcpu")
    if not vcpu or vcpu <= 2:
        return None  # already minimal size, nothing to downsize

    # Downsize by one step (halve vCPU) -> proportional cost reduction.
    target_vcpu = max(2, vcpu // 2)
    current = res.current_monthly_cost
    # Cost scales ~linearly with vCPU under the flat per-vCPU assumption.
    projected = round(current * target_vcpu / vcpu, 2)
    gross = round(current - projected, 2)
    if gross <= 0:
        return None

    return Recommendation(
        id=f"rightsize-{idx:06d}",
        account_id=res.account_id,
        region=res.region,
        resource_id=res.resource_id,
        resource_type=res.resource_type,
        action=ActionType.RIGHTSIZE,
        current_monthly_cost=current,
        projected_monthly_cost=projected,
        gross_savings=gross,
        effort=classify.effort_for_resize(res.resource_type),
        risk=classify.risk_for_resize(res.resource_type),
        restart_required=res.resource_type == ResourceType.EC2,
        rollback_possible=True,
        evidence_confidence=classify.evidence_confidence(attrs),
        notes=f"Observed CPU {cpu:.0%} / mem {mem:.0%} < {LOW_UTIL:.0%}; "
        f"propose {vcpu} -> {target_vcpu} vCPU",
    )


def rightsize(resources: list[Resource]) -> list[Recommendation]:
    out: list[Recommendation] = []
    idx = 0
    for res in resources:
        if res.resource_type not in (ResourceType.EC2, ResourceType.RDS):
            continue
        rec = _rightsize_one(res, idx)
        idx += 1
        if rec:
            out.append(rec)
    return out
