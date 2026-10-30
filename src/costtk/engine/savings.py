"""Savings ledger — track gross/actionable/approved/realized vs. estimated/verified.

Two orthogonal concepts are handled here:

1. **Savings stage** (pipeline): gross → actionable (after dedupe) → approved
   (human sign-off) → realized (actually implemented). Only actionable savings
   are financial-relevant for the "estimated savings" KPI.

2. **Financial classification**: ESTIMATED vs VERIFIED. Nothing produced by the
   synthetic engine is ever VERIFIED — verified requires real billing evidence,
   which this toolkit does not fabricate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import (
    Recommendation,
    RecommendationStatus,
    SavingsClassification,
)


@dataclass
class SavingsLedger:
    """Aggregates savings across the recommendation pipeline."""

    gross: float = 0.0
    actionable: float = 0.0
    approved: float = 0.0
    realized: float = 0.0
    recommendations: list[Recommendation] = field(default_factory=list)

    def ingest(self, recommendations: list[Recommendation]) -> None:
        self.recommendations = recommendations
        self.gross = round(sum(r.gross_savings for r in recommendations), 2)
        self.actionable = round(sum(r.net_savings for r in recommendations), 2)
        # Stages are cumulative: approved includes implemented; realized is the
        # terminal implemented stage. Use an ordered progression.
        _order = [
            RecommendationStatus.PROPOSED,
            RecommendationStatus.REVIEWED,
            RecommendationStatus.APPROVED,
            RecommendationStatus.IMPLEMENTED,
        ]

        def at_least(status: RecommendationStatus) -> float:
            return round(
                sum(r.net_savings for r in recommendations if _order.index(r.status) >= _order.index(status)),
                2,
            )

        self.approved = at_least(RecommendationStatus.APPROVED)
        self.realized = round(
            sum(
                r.net_savings
                for r in recommendations
                if r.status == RecommendationStatus.IMPLEMENTED
            ),
            2,
        )

    @property
    def verified_realized(self) -> float:
        """Realized savings backed by actual billing evidence only."""
        return round(
            sum(
                r.net_savings
                for r in self.recommendations
                if r.status == RecommendationStatus.IMPLEMENTED
                and r.classification == SavingsClassification.VERIFIED
            ),
            2,
        )

    def applies_to(self, current_monthly_cost: float) -> float:
        """Estimated savings as a fraction of current cost (0..1)."""
        if current_monthly_cost <= 0:
            return 0.0
        return round(self.actionable / current_monthly_cost, 4)


def make_savings_classification(
    status: RecommendationStatus,
    has_billing_evidence: bool = False,
) -> SavingsClassification:
    """Classification is derived from evidence, never assumed."""
    if status == RecommendationStatus.IMPLEMENTED and has_billing_evidence:
        return SavingsClassification.VERIFIED
    return SavingsClassification.ESTIMATED
