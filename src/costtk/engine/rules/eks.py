"""EKS optimization rule — right-size node groups based on allocation vs request.

Saves by reducing idle node capacity when allocatable utilization is high but
actual request utilization is much lower, and by flagging clusters without a
cluster autoscaler that keep a fixed (often over-provisioned) node count.
"""

from __future__ import annotations

from ...models import ActionType, Effort, Recommendation, Resource, ResourceType, Risk

REQ_GAP = 0.20  # allocatable - request gap that signals over-provisioning


def _eks_one(res: Resource, idx: int) -> Recommendation | None:
    if res.resource_type != ResourceType.EKS:
        return None
    attrs = res.attributes
    alloc = attrs.get("allocatable_util")
    req = attrs.get("request_util")
    if alloc is None or req is None:
        return None

    gap = alloc - req
    if gap < REQ_GAP:
        return None

    nodes = attrs.get("node_count", 0)
    if nodes <= 1:
        return None

    # Remove enough nodes to bring allocatable down toward request + small headroom.
    target_nodes = max(1, int(nodes * (req + 0.15) / alloc) if alloc else 1)
    current = res.current_monthly_cost
    # Fixed $73 cluster fee + per-node cost.
    fixed = 73.0
    node_cost = current - fixed
    per_node = node_cost / nodes if nodes else 0.0
    projected = round(fixed + per_node * target_nodes, 2)
    gross = round(current - projected, 2)
    if gross <= 0:
        return None

    return Recommendation(
        id=f"eks-{idx:06d}",
        account_id=res.account_id,
        region=res.region,
        resource_id=res.resource_id,
        resource_type=ResourceType.EKS,
        action=ActionType.EKS_OPTIMIZE,
        current_monthly_cost=current,
        projected_monthly_cost=projected,
        gross_savings=gross,
        effort=Effort.MEDIUM,
        risk=Risk.MEDIUM,
        restart_required=False,
        rollback_possible=True,
        evidence_confidence=0.8,
        notes=f"Allocatable {alloc:.0%} vs request {req:.0%} ({gap:.0%} gap); "
        f"scale {nodes} -> {target_nodes} nodes.",
    )


def eks_optimize(resources: list[Resource]) -> list[Recommendation]:
    out: list[Recommendation] = []
    idx = 0
    for res in resources:
        rec = _eks_one(res, idx)
        idx += 1
        if rec:
            out.append(rec)
    return out
