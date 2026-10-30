"""Classification tests — effort/risk/restart/rollback/confidence mapping."""

from __future__ import annotations

from costtk.engine import classify
from costtk.models import Effort, ResourceType, Risk


def test_effort_baseline_mapping():
    assert classify.effort_for_action("Purchase Reserved Instances") == Effort.VERY_LOW
    assert classify.effort_for_action("Purchase Savings Plans") == Effort.VERY_LOW
    assert classify.effort_for_action("EBS Upgrade") == Effort.VERY_LOW
    assert classify.effort_for_action("Migrate to Graviton") == Effort.HIGH
    assert classify.effort_for_action("Rightsize") == Effort.MEDIUM


def test_risk_baseline_mapping():
    assert classify.risk_for_action("Stop Idle") == Risk.LOW
    assert classify.risk_for_resize(ResourceType.RDS) == Risk.HIGH
    assert classify.risk_for_resize(ResourceType.EC2) == Risk.MEDIUM


def test_restart_required_only_for_compute_physical_changes():
    assert classify.restart_required_for("Rightsize", ResourceType.EC2) is True
    assert classify.restart_required_for("Migrate to Graviton", ResourceType.RDS) is True
    assert classify.restart_required_for("EBS Upgrade", ResourceType.EBS) is False
    assert classify.restart_required_for("Rightsize", ResourceType.EBS) is False


def test_evidence_confidence_full_partial_none():
    assert classify.evidence_confidence({"a": 1, "b": 2}) == 1.0
    assert classify.evidence_confidence({"a": 1, "b": None}) == 0.5
    assert classify.evidence_confidence({}) == 0.0


def test_unknown_action_falls_back_to_medium():
    assert classify.effort_for_action("Nonexistent") == Effort.MEDIUM
    assert classify.risk_for_action("Nonexistent") == Risk.MEDIUM
