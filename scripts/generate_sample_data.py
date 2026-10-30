#!/usr/bin/env python3
"""Generate the deterministic synthetic inventory and run the analysis.

Writes two artifacts:
  - data/synthesized/inventory.json   (raw resources)
  - data/synthesized/recommendations.json (post-dedupe recommendations + summary)

The savings percentage is *computed* by the engine from the documented pricing
assumptions — it is never hardcoded here.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from costtk.engine.engine import RecommendationEngine  # noqa: E402
from costtk.models import Resource  # noqa: E402
from costtk.providers.sample import SyntheticProvider  # noqa: E402


def _to_dict(obj):
    if is_dataclass(obj):
        return {k: _to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return list(obj)
    return obj


def main() -> int:
    out_dir = Path("data/synthesized")
    out_dir.mkdir(parents=True, exist_ok=True)

    provider = SyntheticProvider(seed=42)
    engine = RecommendationEngine(provider)
    result = engine.analyze()

    inventory = [asdict(r) for r in result.resources]
    (out_dir / "inventory.json").write_text(json.dumps(inventory, indent=2, default=str))

    summary = {
        "baseline_monthly_cost": result.baseline_monthly_cost,
        "projected_monthly_cost": result.projected_monthly_cost,
        "gross_savings": result.ledger.gross,
        "actionable_savings": result.ledger.actionable,
        "savings_percentage": result.savings_percentage,
        "annualized_savings": round(result.ledger.actionable * 12, 2),
        "resource_count": len(result.resources),
        "recommendation_count": len(result.recommendations),
    }
    payload = {
        "summary": summary,
        "recommendations": [_to_dict(r) for r in result.recommendations],
    }
    (out_dir / "recommendations.json").write_text(json.dumps(payload, indent=2, default=str))

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
