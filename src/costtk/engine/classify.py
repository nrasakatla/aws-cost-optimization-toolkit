"""Classification helpers — effort, risk, confidence.

These map a recommendation's intrinsic properties (action type, resource family,
evidence completeness) to operational risk & effort signals. Centralized so the
dashboard and rules share identical logic instead of duplicating thresholds.
"""

from __future__ import annotations

from typing import Any

from ..models import Effort, ResourceType, Risk

# Effort by action type (default; rules may override for special cases).
_EFFORT_BY_ACTION: dict[str, Effort] = {
    "Rightsize": Effort.MEDIUM,
    "Stop Idle": Effort.LOW,
    "Schedule": Effort.MEDIUM,
    "Migrate to Graviton": Effort.HIGH,
    "Purchase Savings Plans": Effort.VERY_LOW,
    "Purchase Reserved Instances": Effort.VERY_LOW,
    "EBS Upgrade": Effort.VERY_LOW,
    "NAT Gateway Optimize": Effort.MEDIUM,
    "EKS Optimize": Effort.MEDIUM,
    "Storage Retention": Effort.LOW,
}

# Baseline risk by action type.
_RISK_BY_ACTION: dict[str, Risk] = {
    "Rightsize": Risk.MEDIUM,
    "Stop Idle": Risk.LOW,
    "Schedule": Risk.MEDIUM,
    "Migrate to Graviton": Risk.MEDIUM,
    "Purchase Savings Plans": Risk.LOW,
    "Purchase Reserved Instances": Risk.LOW,
    "EBS Upgrade": Risk.LOW,
    "NAT Gateway Optimize": Risk.LOW,
    "EKS Optimize": Risk.MEDIUM,
    "Storage Retention": Risk.LOW,
}

_BOOL_HARD_ACTIONS = {
    "Migrate to Graviton",
    "Rightsize",
}


def effort_for_action(action: str) -> Effort:
    return _EFFORT_BY_ACTION.get(action, Effort.MEDIUM)


def risk_for_action(action: str) -> Risk:
    return _RISK_BY_ACTION.get(action, Risk.MEDIUM)


def effort_for_resize(resource: ResourceType | None = None) -> Effort:
    # Resizing a database is riskier / higher effort than a stateless instance.
    if resource == ResourceType.RDS:
        return Effort.HIGH
    return Effort.MEDIUM


def risk_for_resize(resource: ResourceType | None = None) -> Risk:
    if resource == ResourceType.RDS:
        return Risk.HIGH
    return Risk.MEDIUM


def restart_required_for(action: str, resource_type: ResourceType | None) -> bool:
    if action in ("Rightsize", "Migrate to Graviton"):
        return resource_type in (ResourceType.EC2, ResourceType.RDS)
    return False


def evidence_confidence(attrs: dict[str, Any]) -> float:
    """Confidence 0..1 based on how complete the evidence is.

    Fewer measured signals -> lower confidence. Missing signals are *not*
    treated as zero; they simply lower confidence (and, in rules, block emission).
    """
    measured = sum(1 for v in attrs.values() if v is not None)
    total = len(attrs)
    if total == 0:
        return 0.0
    return round(min(1.0, measured / total), 2)
