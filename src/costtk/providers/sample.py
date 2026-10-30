"""Deterministic synthetic AWS dataset.

This generator models a plausible multi-account, multi-region AWS estate with
documented pricing assumptions. Every number is derived from a fixed seed so the
demo is fully reproducible. Nothing here references live AWS data.

Pricing assumptions are centralized in :data:`ASSUMPTIONS` and documented in
``docs/pricing-assumptions.md``. The engine computes savings from *these*
assumptions plus per-resource utilization signals — the 35% outcome is an
emergent property of the scenario, not a hardcoded constant.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..models import Account, Resource, ResourceType
from .base import Provider


@dataclass(frozen=True)
class PricingAssumptions:
    """Documented unit-price assumptions used by the synthetic scenario (USD/month)."""

    # EC2 on-demand (per vCPU-hour, rounded to monthly for clarity). Note these
    # are *assumptions* chosen to be realistic orders of magnitude, not quotes.
    ec2_x86_per_vcpu_month: float = 4.2  # ~$0.0058/vCPU-hr (medium/large types)
    ec2_graviton_per_vcpu_month: float = 3.36  # ~20% cheaper than x86
    ebs_gp2_per_gb_month: float = 0.10
    ebs_gp3_per_gb_month: float = 0.08  # 20% cheaper + free baseline IOPS
    rds_per_vcpu_month: float = 10.0
    elasticache_per_node_month: float = 40.0
    opensearch_per_node_month: float = 40.0
    nat_hourly: float = 0.045  # per hour
    nat_data_per_gb: float = 0.045
    elb_per_lcu_month: float = 5.0
    s3_per_gb_month: float = 0.023
    cloudwatch_log_per_gb_month: float = 0.25


ASSUMPTIONS = PricingAssumptions()

HOURS_PER_MONTH = 730.0

# Fictional account identifiers (12 digits, clearly marked synthetic).
_ACCOUNTS = [
    ("100000000011", "Platform Engineering"),
    ("100000000022", "Data Platform"),
    ("100000000033", "Customer Facing Services"),
    ("100000000044", "ML & Analytics"),
]

_REGIONS = ["us-east-1", "us-west-2", "eu-west-1"]

_ENVIRONMENTS = ["prod", "staging", "dev", "test"]


class SyntheticProvider(Provider):
    """Deterministic synthetic multi-account inventory source."""

    name = "sample"

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self.assumptions = ASSUMPTIONS

    def collect_accounts(self) -> list[Account]:
        return [Account(account_id=a, name=n, tags={"synthetic": "true"}) for a, n in _ACCOUNTS]

    def _ec2(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            arch = self._rng.choice(["x86", "graviton"]) if env == "prod" else "x86"
            # Prod runs large instances; non-prod runs small ephemeral instances.
            vcpu = self._rng.choice([8, 16, 32, 64]) if env == "prod" else self._rng.choice([2, 4, 8])
            # Utilization signals: prod workloads are mixed; a substantial share is
            # over-provisioned (low util) -> rightsize/commitment candidates.
            # Non-prod is frequently idle or left running 24/7 unnecessarily.
            if env == "prod":
                # Bimodal: either clearly over-provisioned (right-size target) or
                # clearly steady (commitment target). Little dead zone in between.
                cpu_util = self._rng.choice(
                    [self._rng.uniform(0.05, 0.35), self._rng.uniform(0.55, 0.9)]
                )
            else:
                cpu_util = self._rng.uniform(0.02, 0.5)
            is_idle = env != "prod" and cpu_util < 0.08
            if env == "prod" and self._rng.random() < 0.05:
                is_idle = True  # rare orphaned prod instance
            per_vcpu = (
                self.assumptions.ec2_graviton_per_vcpu_month
                if arch == "graviton"
                else self.assumptions.ec2_x86_per_vcpu_month
            )
            monthly = round(per_vcpu * vcpu, 2)
            rid = f"i-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.EC2,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"team-{account_id[-2:]}",
                    attributes={
                        "arch": arch,
                        "vcpu": vcpu,
                        "cpu_util": round(cpu_util, 3),
                        # Memory utilization is correlated with CPU (an over-provisioned
                        # instance is idle on both axes), plus mild jitter.
                        "mem_util": round(
                            min(0.95, max(0.05, cpu_util + self._rng.uniform(-0.08, 0.08))), 3
                        ),
                        "net_util": round(self._rng.uniform(0.0, 0.5), 3),
                        "is_idle": is_idle,
                        "ebs_attached_gb": vcpu * 50,
                        "running_hours_per_month": 730.0,
                        "instance_family": "m7g" if arch == "graviton" else "m6i",
                    },
                )
            )
        return out

    def _ebs(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            size_gb = self._rng.choice([50, 100, 200, 500])
            vol_type = self._rng.choice(["gp2", "gp3"])
            per_gb = (
                self.assumptions.ebs_gp3_per_gb_month
                if vol_type == "gp3"
                else self.assumptions.ebs_gp2_per_gb_month
            )
            monthly = round(per_gb * size_gb, 2)
            rid = f"vol-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.EBS,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"team-{account_id[-2:]}",
                    attributes={
                        "size_gb": size_gb,
                        "volume_type": vol_type,
                        "iops_util": round(self._rng.uniform(0.0, 1.0), 3),
                        "throughput_util": round(self._rng.uniform(0.0, 1.0), 3),
                        "attached_to": f"i-{account_id[-4:]}-{region[:3]}-{env[:2]}-{(i % 10):03d}",
                        "snapshot_age_days": self._rng.choice([0, 30, 90, 180, 365, 900]),
                    },
                )
            )
        return out

    def _rds(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            vcpu = self._rng.choice([4, 8, 16])
            # Skew toward over-provisioning like EC2 (sized for peak never hit).
            cpu_util = self._rng.uniform(0.04, 0.7)
            monthly = round(self.assumptions.rds_per_vcpu_month * vcpu, 2)
            rid = f"db-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.RDS,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"data-{account_id[-2:]}",
                    attributes={
                        "engine": self._rng.choice(["postgres", "mysql", "aurora-postgres"]),
                        "vcpu": vcpu,
                        "cpu_util": round(cpu_util, 3),
                        "mem_util": round(
                            min(0.95, max(0.05, cpu_util + self._rng.uniform(-0.06, 0.06))), 3
                        ),
                        "storage_gb": vcpu * 100,
                        "multi_az": self._rng.random() < 0.4,
                        "running_hours_per_month": 730.0,
                        "is_idle": env != "prod" and cpu_util < 0.06,
                    },
                )
            )
        return out

    def _eks(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            nodes = self._rng.choice([2, 3, 4, 6])
            vcpu_per_node = 4
            alloc_util = self._rng.uniform(0.2, 0.85)
            # Cluster fixed cost + node cost
            monthly = round(73.0 + nodes * vcpu_per_node * self.assumptions.ec2_x86_per_vcpu_month, 2)
            rid = f"eks-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.EKS,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"platform-{account_id[-2:]}",
                    attributes={
                        "node_count": nodes,
                        "allocatable_util": round(alloc_util, 3),
                        "request_util": round(alloc_util - self._rng.uniform(0.0, 0.25), 3),
                        "cluster_autoscaler": self._rng.random() < 0.7,
                        "running_hours_per_month": 730.0,
                    },
                )
            )
        return out

    def _elb(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            lcu = self._rng.uniform(0.0, 40.0)
            monthly = round(self.assumptions.elb_per_lcu_month * lcu + 16.43, 2)
            rid = f"elb-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.ELB,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"platform-{account_id[-2:]}",
                    attributes={
                        "lcu_util": round(lcu, 2),
                        "active_targets": self._rng.choice([0, 0, 1, 2, 4, 8]),  # some idle
                    },
                )
            )
        return out

    def _nat(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            data_gb = self._rng.uniform(0.0, 2000.0)
            monthly = round(
                self.assumptions.nat_hourly * HOURS_PER_MONTH
                + self.assumptions.nat_data_per_gb * data_gb,
                2,
            )
            rid = f"nat-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.NAT,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"platform-{account_id[-2:]}",
                    attributes={
                        "data_gb_per_month": round(data_gb, 1),
                        "availability_zones": 1,
                        "traffic_through_vpc_endpoints_pct": self._rng.uniform(0.0, 0.6),
                    },
                )
            )
        return out

    def _elasticache(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            nodes = self._rng.choice([1, 2, 3, 4])
            monthly = round(self.assumptions.elasticache_per_node_month * nodes, 2)
            rid = f"ec-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.ELASTICACHE,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"data-{account_id[-2:]}",
                    attributes={
                        "node_count": nodes,
                        "cpu_util": round(self._rng.uniform(0.05, 0.8), 3),
                        "engine": self._rng.choice(["redis", "memcached"]),
                    },
                )
            )
        return out

    def _opensearch(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            nodes = self._rng.choice([2, 3])
            monthly = round(self.assumptions.opensearch_per_node_month * nodes, 2)
            rid = f"os-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.OPENSEARCH,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"data-{account_id[-2:]}",
                    attributes={
                        "node_count": nodes,
                        "cpu_util": round(self._rng.uniform(0.05, 0.85), 3),
                        "storage_util": round(self._rng.uniform(0.1, 0.9), 3),
                    },
                )
            )
        return out

    def _lambda(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            invocations = self._rng.choice([0, 1000, 100_000, 5_000_000])
            monthly = round(self._rng.uniform(0.0, 120.0), 2) if invocations else 0.0
            rid = f"fn-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.LAMBDA,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"team-{account_id[-2:]}",
                    attributes={
                        "invocations_last_month": invocations,
                        "memory_mb": self._rng.choice([128, 256, 512, 1024]),
                        "is_idle": invocations == 0,
                    },
                )
            )
        return out

    def _s3(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            storage_gb = self._rng.uniform(10.0, 8000.0)
            monthly = round(self.assumptions.s3_per_gb_month * storage_gb, 2)
            rid = f"s3-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.S3,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"data-{account_id[-2:]}",
                    attributes={
                        "storage_gb": round(storage_gb, 1),
                        "lifecycle_rule": self._rng.random() < 0.4,
                        "last_access_days": self._rng.choice([30, 90, 180, 365, 700]),
                        "versioning_enabled": self._rng.random() < 0.5,
                    },
                )
            )
        return out

    def _cloudwatch(self, account_id: str, region: str, env: str, n: int) -> list[Resource]:
        out: list[Resource] = []
        for i in range(n):
            log_gb = self._rng.uniform(0.0, 600.0)
            monthly = round(self.assumptions.cloudwatch_log_per_gb_month * log_gb, 2)
            rid = f"log-{account_id[-4:]}-{region[:3]}-{env[:2]}-{i:03d}"
            out.append(
                Resource(
                    resource_id=rid,
                    account_id=account_id,
                    region=region,
                    resource_type=ResourceType.CLOUDWATCH,
                    current_monthly_cost=monthly,
                    environment=env,
                    owner=f"platform-{account_id[-2:]}",
                    attributes={
                        "log_gb_per_month": round(log_gb, 1),
                        "retention_days": self._rng.choice([30, 90, 180, 3650]),
                        "last_scan_days": self._rng.choice([0, 30, 90, 365]),
                    },
                )
            )
        return out

    def collect_resources(self) -> list[Resource]:
        resources: list[Resource] = []
        # Keep the estate modest so the scenario lands near the ~$10k/month
        # baseline. Not every account has every resource type; this mirrors a
        # realistic (non-uniform) footprint.
        for account_id, _name in _ACCOUNTS:
            for region in _REGIONS:
                for env in _ENVIRONMENTS:
                    n_ec2 = 2 if env == "prod" else 1
                    resources += self._ec2(account_id, region, env, n_ec2)
                    resources += self._ebs(account_id, region, env, 1)
                    if env in ("prod", "staging"):
                        resources += self._rds(account_id, region, env, 1)
                # Shared/regional resources (prod only, sparse).
                if _name in ("Platform Engineering", "Data Platform"):
                    resources += self._eks(account_id, region, "prod", 1)
                    resources += self._elb(account_id, region, "prod", 1)
                    resources += self._nat(account_id, region, "prod", 1)
                if _name == "Data Platform":
                    resources += self._elasticache(account_id, region, "prod", 1)
                    resources += self._opensearch(account_id, region, "prod", 1)
                if _name == "Customer Facing Services":
                    resources += self._lambda(account_id, region, "prod", 3)
                if _name in ("Data Platform", "Shared Services"):
                    resources += self._s3(account_id, region, "prod", 1)
                    resources += self._cloudwatch(account_id, region, "prod", 2)
        return resources
