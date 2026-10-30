"""AWS Cost Optimization Toolkit — data models.

Pure dataclasses with no runtime side effects. These are the single source of
truth for the shape of every resource and recommendation flowing through the
engine and into the dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Effort(str, Enum):
    """Implementation effort for a recommendation."""

    VERY_LOW = "Very Low"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class Risk(str, Enum):
    """Operational risk level."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ActionType(str, Enum):
    """Optimization action kinds supported by the engine."""

    RIGHTSIZE = "Rightsize"
    STOP_IDLE = "Stop Idle"
    SCHEDULE = "Schedule"
    GRAVITON = "Migrate to Graviton"
    SAVINGS_PLANS = "Purchase Savings Plans"
    RESERVED_INSTANCES = "Purchase Reserved Instances"
    EBS_UPGRADE = "EBS Upgrade"
    NAT_OPTIMIZE = "NAT Gateway Optimize"
    EKS_OPTIMIZE = "EKS Optimize"
    STORAGE_RETENTION = "Storage Retention"


class RecommendationStatus(str, Enum):
    """Lifecycle status of a recommendation (workflow, not finance)."""

    PROPOSED = "Proposed"
    REVIEWED = "Reviewed"
    APPROVED = "Approved"
    IMPLEMENTED = "Implemented"
    REJECTED = "Rejected"


class SavingsClassification(str, Enum):
    """Financial classification — separates modeled estimates from verified savings."""

    ESTIMATED = "Estimated"
    VERIFIED = "Verified (realized billing)"


class ResourceType(str, Enum):
    """Resource families the engine knows about."""

    EC2 = "EC2 Instance"
    EBS = "EBS Volume"
    RDS = "RDS Instance"
    EKS = "EKS Cluster"
    ELB = "Load Balancer"
    NAT = "NAT Gateway"
    ELASTICACHE = "ElastiCache Node"
    OPENSEARCH = "OpenSearch Domain"
    LAMBDA = "Lambda Function"
    S3 = "S3 Bucket"
    CLOUDWATCH = "CloudWatch Log Group"


@dataclass
class Account:
    account_id: str
    name: str
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Resource:
    """A single modelled AWS resource."""

    resource_id: str
    account_id: str
    region: str
    resource_type: ResourceType
    current_monthly_cost: float
    environment: str  # prod / staging / dev / test
    owner: str | None = None
    dependencies: list[str] = field(default_factory=list)
    # Free-form evidence/attributes bag, e.g. {"vCPU": 8, "cpu_util": 0.12, ...}
    attributes: dict[str, Any] = field(default_factory=dict)
    # Missing evidence keys — the engine treats absence as unknown, not zero.
    missing_evidence: list[str] = field(default_factory=list)


@dataclass
class Recommendation:
    """A single optimization recommendation with full financial + risk context."""

    id: str
    account_id: str
    region: str
    resource_id: str
    resource_type: ResourceType
    action: ActionType
    current_monthly_cost: float
    projected_monthly_cost: float
    gross_savings: float
    # Net non-overlapping savings — populated by the dedupe pass, not by rules.
    net_savings: float = 0.0
    savings_percentage: float = 0.0
    effort: Effort = Effort.MEDIUM
    risk: Risk = Risk.MEDIUM
    restart_required: bool = False
    rollback_possible: bool = True
    status: RecommendationStatus = RecommendationStatus.PROPOSED
    classification: SavingsClassification = SavingsClassification.ESTIMATED
    evidence_confidence: float = 1.0  # 0..1 based on evidence completeness
    dependencies: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def annualized_savings(self) -> float:
        return round(self.net_savings * 12, 2)


def blank_recommendation() -> Recommendation:
    """Minimal valid recommendation used by rule tests."""
    return Recommendation(
        id="blank",
        account_id="000000000000",
        region="us-east-1",
        resource_id="blank",
        resource_type=ResourceType.EC2,
        action=ActionType.RIGHTSIZE,
        current_monthly_cost=0.0,
        projected_monthly_cost=0.0,
        gross_savings=0.0,
    )
