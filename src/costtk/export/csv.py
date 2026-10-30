"""CSV export for recommendations and summary."""

from __future__ import annotations

import csv
from io import StringIO

from ..models import Recommendation


def recommendations_to_csv(recommendations: list[Recommendation]) -> str:
    """Serialize recommendations to a CSV string (RFC-4180)."""
    columns = [
        "id",
        "account_id",
        "region",
        "resource_id",
        "resource_type",
        "action",
        "current_monthly_cost",
        "projected_monthly_cost",
        "gross_savings",
        "net_savings",
        "savings_percentage",
        "effort",
        "risk",
        "restart_required",
        "rollback_possible",
        "status",
        "classification",
        "evidence_confidence",
        "notes",
    ]
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    for r in recommendations:
        row = {
            "resource_type": r.resource_type.value,
            "action": r.action.value,
            "effort": r.effort.value,
            "risk": r.risk.value,
            "status": r.status.value,
            "classification": r.classification.value,
            **{
                k: getattr(r, k)
                for k in columns
                if k
                not in {
                    "resource_type",
                    "action",
                    "effort",
                    "risk",
                    "status",
                    "classification",
                }
            },
        }
        writer.writerow(row)
    return buf.getvalue()


def write_recommendations_csv(recommendations: list[Recommendation], path: str) -> None:
    with open(path, "w", newline="") as fh:
        fh.write(recommendations_to_csv(recommendations))
