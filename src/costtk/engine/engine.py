"""Recommendation engine orchestrator.

Ties providers + rules + classification + dedupe + savings together into a
single analysis pipeline:

    resources -> [rules] -> candidates -> classify -> dedupe -> ledger
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Recommendation, Resource
from ..providers.base import Provider
from . import classify
from .dedupe import deduplicate
from .rules import all_rules
from .savings import SavingsLedger


@dataclass
class AnalysisResult:
    resources: list[Resource] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    ledger: SavingsLedger = field(default_factory=SavingsLedger)
    baseline_monthly_cost: float = 0.0

    @property
    def projected_monthly_cost(self) -> float:
        return round(self.baseline_monthly_cost - self.ledger.actionable, 2)

    @property
    def savings_percentage(self) -> float:
        if self.baseline_monthly_cost <= 0:
            return 0.0
        return round(self.ledger.actionable / self.baseline_monthly_cost * 100, 2)


class RecommendationEngine:
    """Runs the full optimization analysis."""

    def __init__(self, provider: Provider) -> None:
        self.provider = provider
        self.rules = all_rules()

    def analyze(self) -> AnalysisResult:
        resources = self.provider.collect_resources()
        baseline = round(sum(r.current_monthly_cost for r in resources), 2)

        candidates: list[Recommendation] = []
        for rule in self.rules:
            candidates.extend(rule(resources))

        # Classify: preserve rule-assigned effort/risk where a rule made a
        # deliberate choice; only backfill truly-default values from the
        # centralized mapping. Restart is derived deterministically.
        for c in candidates:
            c.restart_required = classify.restart_required_for(
                c.action.value, c.resource_type
            )
            c.savings_percentage = (
                round(c.gross_savings / c.current_monthly_cost * 100, 2)
                if c.current_monthly_cost
                else 0.0
            )

        recommendations = deduplicate(candidates)

        ledger = SavingsLedger()
        ledger.ingest(recommendations)

        return AnalysisResult(
            resources=resources,
            recommendations=recommendations,
            ledger=ledger,
            baseline_monthly_cost=baseline,
        )
