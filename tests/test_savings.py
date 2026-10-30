"""Savings lifecycle tests — stage pipeline + financial classification honesty."""

from __future__ import annotations

from costtk.engine.savings import SavingsLedger, make_savings_classification
from costtk.models import (
    ActionType,
    RecommendationStatus,
    SavingsClassification,
)


def test_ledger_stages(res_factory):
    # Build three recs in different statuses via engine-free construction.
    from costtk.models import Effort, Recommendation, ResourceType, Risk

    def r(rid, status):
        return Recommendation(
            id=f"r-{rid}",
            account_id="1",
            region="us-east-1",
            resource_id=rid,
            resource_type=ResourceType.EC2,
            action=ActionType.RIGHTSIZE,
            current_monthly_cost=100.0,
            projected_monthly_cost=50.0,
            gross_savings=50.0,
            net_savings=50.0,
            effort=Effort.MEDIUM,
            risk=Risk.MEDIUM,
            status=status,
        )

    recs = [
        r("a", RecommendationStatus.PROPOSED),
        r("b", RecommendationStatus.APPROVED),
        r("c", RecommendationStatus.IMPLEMENTED),
    ]
    ledger = SavingsLedger()
    ledger.ingest(recs)
    assert ledger.gross == 150.0
    assert ledger.actionable == 150.0  # all are net 50
    assert ledger.approved == 100.0  # b + c
    assert ledger.realized == 50.0  # c only


def test_verified_requires_billing_evidence():
    rec_status = RecommendationStatus.IMPLEMENTED
    assert make_savings_classification(rec_status, has_billing_evidence=True) == (
        SavingsClassification.VERIFIED
    )
    assert make_savings_classification(rec_status, has_billing_evidence=False) == (
        SavingsClassification.ESTIMATED
    )


def test_never_verified_by_default():
    # Synthetic recommendations must always be ESTIMATED unless explicitly backed.
    assert make_savings_classification(RecommendationStatus.PROPOSED) == (
        SavingsClassification.ESTIMATED
    )
    assert make_savings_classification(RecommendationStatus.APPROVED) == (
        SavingsClassification.ESTIMATED
    )


def test_percentage_bounded():
    ledger = SavingsLedger()
    ledger.actionable = 35.0
    assert ledger.applies_to(100.0) == 0.35
    assert ledger.applies_to(0.0) == 0.0
