"""Rule modules generate candidate recommendations from resources.

Each rule is a pure function: ``resources -> list[Recommendation]``. Rules only
emit a recommendation when the underlying synthetic data actually supports it.
They never fabricate evidence for a missing metric.
"""

from . import (  # noqa: F401
    ebs,
    eks,
    graviton,
    idle,
    nat,
    reserved_instances,
    rightsize,
    savings_plans,
    schedule,
    storage,
)


def all_rules():
    """Return every registered rule function."""
    return [
        rightsize.rightsize,
        idle.idle,
        schedule.schedule,
        eks.eks_optimize,
        ebs.ebs_upgrade,
        savings_plans.savings_plans,
        reserved_instances.reserved_instances,
        graviton.graviton,
        nat.nat_optimize,
        storage.storage_retention,
    ]
