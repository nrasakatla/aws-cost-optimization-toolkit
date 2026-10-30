"""Deduplication — prevent double-counting overlapping recommendations.

Two recommendations "overlap" when they target the same resource and their
effects are not independent (e.g. you cannot both fully rightsize an instance
*and* migrate it to Graviton *and* buy a Savings Plan for it — those savings
overlap on the same compute spend).

Strategy (not "keep the largest"):
- Group recommendations by resource_id.
- Within a group, resolve conflicts by a *precedence* that reflects what a
  FinOps practitioner actually does first: commitments (SP/RI) apply to whatever
  compute remains; rightsizing reduces the base before commitments apply. We
  resolve overlapping physical-change actions (rightsize / graviton / schedule /
  idle-stop) so only the highest-confidence *single* physical change survives,
  then single commitments remain additive against that reduced base.
- The surviving recommendations get `net_savings = gross_savings` and a note of
  what was dropped (`deduped_from`).

The result: overlapping recommendations are never summed; the net savings is the
non-overlapping total.
"""

from __future__ import annotations

from collections import defaultdict

from ..models import ActionType, Recommendation

# Actions that change the physical resource footprint (mutually exclusive on a
# single resource). Order = precedence (first wins the physical change).
PHYSICAL_ACTIONS = [
    ActionType.STOP_IDLE,
    ActionType.RIGHTSIZE,
    ActionType.GRAVITON,
    ActionType.SCHEDULE,
]

# Commitment/discount actions — these stack with a physical change but can also
# conflict with each other on the same resource.
COMMITMENT_ACTIONS = [
    ActionType.SAVINGS_PLANS,
    ActionType.RESERVED_INSTANCES,
]


def _same_resource(a: Recommendation, b: Recommendation) -> bool:
    return a.resource_id == b.resource_id and a.account_id == b.account_id


def deduplicate(
    recommendations: list[Recommendation],
    keep_overlaps: bool = False,
) -> list[Recommendation]:
    """Return recommendations with overlapping physical changes collapsed.

    ``kept`` recommendations carry non-overlapping ``net_savings``. Overlapping
    physical actions are reduced to one survivor per resource (highest
    confidence, then highest gross savings as tie-break); commitments remain but
    are re-based against the reduced physical footprint.
    """
    if keep_overlaps:
        for r in recommendations:
            r.net_savings = r.gross_savings
        return recommendations

    by_resource: dict[tuple[str, str], list[Recommendation]] = defaultdict(list)
    for r in recommendations:
        by_resource[(r.account_id, r.resource_id)].append(r)

    result: list[Recommendation] = []
    for group in by_resource.values():
        physical = [r for r in group if r.action in PHYSICAL_ACTIONS]
        commitments = [r for r in group if r.action in COMMITMENT_ACTIONS]
        others = [r for r in group if r.action not in PHYSICAL_ACTIONS + COMMITMENT_ACTIONS]

        survivor: Recommendation | None = None
        dropped: list[Recommendation] = []
        if physical:
            # Pick highest-confidence, tie-break by gross savings.
            physical_sorted = sorted(
                physical, key=lambda r: (r.evidence_confidence, r.gross_savings), reverse=True
            )
            survivor = physical_sorted[0]
            dropped = physical_sorted[1:]

        if survivor is not None:
            survivor.net_savings = survivor.gross_savings
            if dropped:
                survivor.dependencies = list(
                    dict.fromkeys(survivor.dependencies + [d.id for d in dropped])
                )
                survivor.notes += (
                    " [deduped: " + ", ".join(d.action.value for d in dropped) + "]"
                )
            result.append(survivor)

        # Commitments apply to the reduced base when a physical change exists;
        # otherwise they apply to full cost. Mark appropriately.
        for c in commitments:
            if survivor is not None:
                # Re-base commitment saving on the post-physical-change cost.
                base = survivor.projected_monthly_cost
                scaled = round(
                    c.gross_savings * (base / c.current_monthly_cost)
                    if c.current_monthly_cost
                    else 0.0,
                    2,
                )
                c.net_savings = max(0.0, min(scaled, c.gross_savings))
                c.dependencies.append(survivor.id)
                c.notes += " [commitment re-based after physical change]"
            else:
                c.net_savings = c.gross_savings
            result.append(c)

        for o in others:
            o.net_savings = o.gross_savings
            result.append(o)

    return result
