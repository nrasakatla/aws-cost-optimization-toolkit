"""Offline operation + export + no-AWS-calls tests."""

from __future__ import annotations

import csv
import io

from costtk.export.csv import recommendations_to_csv
from costtk.providers.sample import SyntheticProvider


def test_csv_export_round_trips():
    provider = SyntheticProvider(seed=42)
    from costtk.engine.engine import RecommendationEngine

    result = RecommendationEngine(provider).analyze()
    csv_text = recommendations_to_csv(result.recommendations)
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) == len(result.recommendations)
    assert reader.fieldnames is not None
    for col in (
        "account_id",
        "region",
        "resource_type",
        "action",
        "gross_savings",
        "net_savings",
    ):
        assert col in reader.fieldnames


def test_offline_no_aws_import_executed():
    """The demo path must not import/execute boto3 live calls.

    We prove this by importing the package and checking that no boto3 client is
    created during a normal analysis run. boto3 itself may be importable, but the
    synthetic path must never instantiate a client.
    """
    import boto3  # noqa: F401  (import-only is fine; no client construction)

    from costtk.engine.engine import RecommendationEngine
    from costtk.providers.sample import SyntheticProvider

    # Monkeypatch-patch boto3.client to fail if called during analysis.
    original = boto3.client

    def _fail(*a, **k):
        raise AssertionError("boto3.client() was called during synthetic analysis!")

    boto3.client = _fail
    try:
        result = RecommendationEngine(SyntheticProvider(seed=42)).analyze()
        assert result.baseline_monthly_cost > 0
    finally:
        boto3.client = original
