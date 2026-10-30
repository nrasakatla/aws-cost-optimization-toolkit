"""Shared pytest fixtures — deterministic, no AWS calls."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the package is importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from costtk.models import (  # noqa: E402
    ActionType,
    Effort,
    Recommendation,
    Resource,
    ResourceType,
    Risk,
)


def make_rec(
    resource_id="res-1",
    action=ActionType.RIGHTSIZE,
    gross=100.0,
    current=200.0,
    resource_type=ResourceType.EC2,
    account="100000000001",
    confidence=1.0,
) -> Recommendation:
    return Recommendation(
        id=f"{action.value.lower()}-{resource_id}",
        account_id=account,
        region="us-east-1",
        resource_id=resource_id,
        resource_type=resource_type,
        action=action,
        current_monthly_cost=current,
        projected_monthly_cost=round(current - gross, 2),
        gross_savings=gross,
        effort=Effort.MEDIUM,
        risk=Risk.MEDIUM,
        evidence_confidence=confidence,
    )


def make_resource(
    resource_id="res-1",
    rtype=ResourceType.EC2,
    cost=100.0,
    env="prod",
    attrs=None,
) -> Resource:
    return Resource(
        resource_id=resource_id,
        account_id="100000000001",
        region="us-east-1",
        resource_type=rtype,
        current_monthly_cost=cost,
        environment=env,
        attributes=attrs or {},
    )


@pytest.fixture
def rec_factory():
    return make_rec


@pytest.fixture
def res_factory():
    return make_resource
