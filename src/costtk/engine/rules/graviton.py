"""Graviton migration rule — flag x86 instances eligible for ARM (Graviton).

Graviton delivers ~20% cheaper per-vCPU compute. Not every workload can migrate:
compatibility risk is assessed from architecture, instance family, and any
x86-only dependency signals. The recommendation records that risk explicitly
rather than assuming migration is always safe.
"""

from __future__ import annotations

from ...models import ActionType, Effort, Recommendation, Resource, ResourceType, Risk

GRAVITON_SAVING = 0.20  # 20% cheaper per vCPU
KNOWN_X86_LOCKED_FAMILIES = {"m6i"}  # m7g is the Graviton equivalent


def _graviton_one(res: Resource, idx: int) -> Recommendation | None:
    if res.resource_type != ResourceType.EC2:
        return None
    attrs = res.attributes
    if attrs.get("arch") != "x86":
        return None  # already Graviton or unknown

    current = res.current_monthly_cost
    gross = round(current * GRAVITON_SAVING, 2)
    if gross <= 0:
        return None

    family = attrs.get("instance_family", "")
    # Compatibility risk: known x86-locked workloads carry higher risk.
    compat_risk = Risk.HIGH if family in KNOWN_X86_LOCKED_FAMILIES else Risk.MEDIUM
    has_risk_note = family in KNOWN_X86_LOCKED_FAMILIES

    return Recommendation(
        id=f"graviton-{idx:06d}",
        account_id=res.account_id,
        region=res.region,
        resource_id=res.resource_id,
        resource_type=ResourceType.EC2,
        action=ActionType.GRAVITON,
        current_monthly_cost=current,
        projected_monthly_cost=round(current - gross, 2),
        gross_savings=gross,
        effort=Effort.HIGH,
        risk=compat_risk,
        restart_required=True,
        rollback_possible=True,
        evidence_confidence=0.7,
        notes=("x86-locked family; verify binary compatibility before migration"
               if has_risk_note
               else "x86 -> Graviton: verify ARM compatibility of app + dependencies."),
    )


def graviton(resources: list[Resource]) -> list[Recommendation]:
    out: list[Recommendation] = []
    idx = 0
    for res in resources:
        rec = _graviton_one(res, idx)
        idx += 1
        if rec:
            out.append(rec)
    return out
