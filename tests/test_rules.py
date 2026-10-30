"""Rule correctness tests — evidence gating, no zero-implied-usage."""

from __future__ import annotations

from costtk.engine.rules import graviton, idle, reserved_instances, rightsize, savings_plans
from costtk.models import ActionType, ResourceType


def test_rightsize_requires_both_metrics(res_factory):
    # Missing mem_util -> no recommendation (do not imply zero).
    res = res_factory(
        rtype=ResourceType.EC2,
        cost=100.0,
        attrs={"vcpu": 8, "cpu_util": 0.1},  # mem_util missing
    )
    assert rightsize.rightsize([res]) == []


def test_rightsize_low_util_present(res_factory):
    res = res_factory(
        rtype=ResourceType.EC2,
        cost=100.0,
        attrs={"vcpu": 8, "cpu_util": 0.1, "mem_util": 0.1},
    )
    out = rightsize.rightsize([res])
    assert len(out) == 1
    assert out[0].action == ActionType.RIGHTSIZE
    assert out[0].gross_savings > 0
    assert out[0].gross_savings < out[0].current_monthly_cost


def test_rightsize_skips_high_util(res_factory):
    res = res_factory(
        rtype=ResourceType.EC2,
        cost=100.0,
        attrs={"vcpu": 8, "cpu_util": 0.9, "mem_util": 0.9},
    )
    assert rightsize.rightsize([res]) == []


def test_rightsize_skips_already_minimal(res_factory):
    res = res_factory(
        rtype=ResourceType.EC2,
        cost=10.0,
        attrs={"vcpu": 2, "cpu_util": 0.1, "mem_util": 0.1},
    )
    assert rightsize.rightsize([res]) == []


def test_rightsize_rds_is_high_risk(res_factory):
    res = res_factory(
        rtype=ResourceType.RDS,
        cost=200.0,
        attrs={"vcpu": 16, "cpu_util": 0.1, "mem_util": 0.1},
    )
    out = rightsize.rightsize([res])
    assert len(out) == 1
    assert out[0].risk.value == "High"
    assert out[0].effort.value == "High"


def test_idle_requires_corroborating_signals(res_factory):
    # cpu_util high but is_idle True -> contradictory -> skip.
    res = res_factory(
        rtype=ResourceType.EC2,
        cost=100.0,
        attrs={"is_idle": True, "cpu_util": 0.5},
    )
    assert idle.idle([res]) == []


def test_idle_missing_flag_skips(res_factory):
    res = res_factory(rtype=ResourceType.EC2, cost=100.0, attrs={})
    assert idle.idle([res]) == []


def test_graviton_only_x86(res_factory):
    res = res_factory(
        rtype=ResourceType.EC2,
        cost=100.0,
        attrs={"arch": "graviton"},
    )
    assert graviton.graviton([res]) == []


def test_graviton_x86_flags_risk(res_factory):
    res = res_factory(
        rtype=ResourceType.EC2,
        cost=100.0,
        attrs={"arch": "x86", "instance_family": "m6i"},
    )
    out = graviton.graviton([res])
    assert len(out) == 1
    assert out[0].action == ActionType.GRAVITON
    assert out[0].risk.value == "High"  # x86-locked family


def test_savings_plans_requires_steady_always_on(res_factory):
    # Low util -> not steady -> no SP.
    res = res_factory(
        rtype=ResourceType.EC2,
        cost=100.0,
        attrs={"cpu_util": 0.3, "running_hours_per_month": 730.0},
    )
    assert savings_plans.savings_plans([res]) == []


def test_savings_plans_steady(res_factory):
    res = res_factory(
        rtype=ResourceType.EC2,
        cost=100.0,
        attrs={"cpu_util": 0.8, "running_hours_per_month": 730.0},
    )
    out = savings_plans.savings_plans([res])
    assert len(out) == 1
    assert out[0].action == ActionType.SAVINGS_PLANS


def test_reserved_instances_only_prod(res_factory):
    res = res_factory(
        rtype=ResourceType.RDS,
        cost=100.0,
        env="staging",
        attrs={"running_hours_per_month": 730.0},
    )
    assert reserved_instances.reserved_instances([res]) == []
