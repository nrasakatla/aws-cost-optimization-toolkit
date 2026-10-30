"""Deduplication tests — no double-counting of overlapping recommendations."""

from __future__ import annotations

from costtk.engine.dedupe import deduplicate
from costtk.models import ActionType


def test_distinct_resources_all_kept(rec_factory):
    recs = [
        rec_factory(resource_id="a", action=ActionType.RIGHTSIZE, gross=100.0),
        rec_factory(resource_id="b", action=ActionType.RIGHTSIZE, gross=50.0),
    ]
    out = deduplicate(recs)
    assert len(out) == 2
    assert sum(r.net_savings for r in out) == 150.0


def test_overlapping_physical_actions_collapsed(rec_factory):
    # Same resource, two mutually-exclusive physical changes.
    recs = [
        rec_factory(resource_id="x", action=ActionType.RIGHTSIZE, gross=100.0, confidence=0.9),
        rec_factory(resource_id="x", action=ActionType.GRAVITON, gross=40.0, confidence=0.5),
    ]
    out = deduplicate(recs)
    physical = [r for r in out if r.action in (ActionType.RIGHTSIZE, ActionType.GRAVITON)]
    assert len(physical) == 1
    survivor = physical[0]
    assert survivor.action == ActionType.RIGHTSIZE  # higher confidence wins
    assert survivor.net_savings == 100.0
    # Dropped one must be recorded.
    assert any("deduped" in survivor.notes.lower() for r in [survivor])


def test_overlap_not_summed(rec_factory):
    recs = [
        rec_factory(resource_id="x", action=ActionType.RIGHTSIZE, gross=100.0),
        rec_factory(resource_id="x", action=ActionType.GRAVITON, gross=100.0),
        rec_factory(resource_id="x", action=ActionType.SCHEDULE, gross=100.0),
    ]
    out = deduplicate(recs)
    total = sum(r.net_savings for r in out)
    # Overlapping physical changes on one resource -> only one survivor, not 300.
    assert total < 300.0


def test_commitment_rebased_after_physical_change(rec_factory):
    # Rightsize (physical) + Savings Plan (commitment) on the same resource.
    # The SP should be re-based onto the post-rightsize cost, not full cost.
    recs = [
        rec_factory(
            resource_id="x",
            action=ActionType.RIGHTSIZE,
            gross=100.0,
            current=200.0,
            confidence=1.0,
        ),
        rec_factory(
            resource_id="x",
            action=ActionType.SAVINGS_PLANS,
            gross=56.0,  # 28% of 200
            current=200.0,
        ),
    ]
    out = deduplicate(recs)
    sp = [r for r in out if r.action == ActionType.SAVINGS_PLANS][0]
    # Rightsize projected cost = 100; SP 28% of 100 = 28.
    assert sp.net_savings == 28.0
    assert sp.net_savings < sp.gross_savings


def test_rightsize_beats_lower_confidence_graviton_only_by_confidence(rec_factory):
    # Tie-break: equal confidence -> higher gross wins.
    recs = [
        rec_factory(resource_id="x", action=ActionType.GRAVITON, gross=80.0, confidence=0.9),
        rec_factory(resource_id="x", action=ActionType.RIGHTSIZE, gross=100.0, confidence=0.9),
    ]
    out = deduplicate(recs)
    physical = [r for r in out if r.action in (ActionType.RIGHTSIZE, ActionType.GRAVITON)]
    assert len(physical) == 1
    assert physical[0].action == ActionType.RIGHTSIZE  # higher gross on tie


def test_no_overlap_when_keep_overlaps(rec_factory):
    recs = [
        rec_factory(resource_id="x", action=ActionType.RIGHTSIZE, gross=100.0),
        rec_factory(resource_id="x", action=ActionType.GRAVITON, gross=40.0),
    ]
    out = deduplicate(recs, keep_overlaps=True)
    assert len(out) == 2
    assert sum(r.net_savings for r in out) == 140.0
