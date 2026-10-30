# Pricing Assumptions (Synthetic Scenario)

> All figures below are **documented modeling assumptions**, chosen to be
> realistic orders of magnitude for a demo. They are **not** AWS published
> prices, are not quotes, and do not reflect any real customer billing.

The engine computes every savings figure from these assumptions plus
per-resource utilization signals. No dollar amount anywhere in the output is
hardcoded to force a target percentage.

## Unit price assumptions (USD)

| Resource | Assumption | Value | Basis |
|---|---|---|---|
| EC2 x86 compute | `ec2_x86_per_vcpu_month` | $4.20 / vCPU-month | ~$0.0058 / vCPU-hr |
| EC2 Graviton compute | `ec2_graviton_per_vcpu_month` | $3.36 / vCPU-month | ~20% cheaper than x86 |
| EBS gp2 | `ebs_gp2_per_gb_month` | $0.10 / GB-month | standard gp2 storage |
| EBS gp3 | `ebs_gp3_per_gb_month` | $0.08 / GB-month | 20% cheaper than gp2 |
| RDS compute | `rds_per_vcpu_month` | $10.00 / vCPU-month | managed DB premium over EC2 |
| ElastiCache node | `elasticache_per_node_month` | $40.00 / node-month | cache.r6g.large-class |
| OpenSearch node | `opensearch_per_node_month` | $40.00 / node-month | t3.small.search-class |
| NAT Gateway hourly | `nat_hourly` | $0.045 / hr | per-hour service fee |
| NAT data processing | `nat_data_per_gb` | $0.045 / GB | per-GB data charge |
| Load Balancer | `elb_per_lcu_month` | $5.00 / LCU-month | ~$0.0068 / LCU-hr |
| S3 standard | `s3_per_gb_month` | $0.023 / GB-month | standard tier |
| CloudWatch logs | `cloudwatch_log_per_gb_month` | $0.25 / GB-month | ingest+store |

## Discount assumptions (recommendation yield)

| Recommendation | Discount | Rationale |
|---|---|---|
| Savings Plans (Compute) | 28% | 1-yr, no-upfront, any region/family |
| Reserved Instances (RDS/ElastiCache/OpenSearch) | 42% | 1-yr, no-upfront, region+type locked |
| Graviton migration | 20% | x86 -> ARM per-vCPU price delta |
| EBS gp2 -> gp3 | 20% | per-GB price delta |
| S3 Infrequent Access | 60% | storage tier price delta |
| Rightsize / EKS optimize | proportional | cost scales ~linearly with capacity |

## Capacity / utilization rules

- **Rightsize** fires when CPU *and* memory utilization are both < 40% (both
  axes must be measured; a missing metric blocks the recommendation, never
  defaults to zero). Sizing is reduced one step (halve vCPU) at a time.
- **Idle** requires corroborating signals (a resource is flagged idle *and*
  utilization is effectively zero) — multiple signals, not one noisy metric.
- **Schedule** applies only to non-production (`staging/dev/test`), reducing to
  12 h/day runtime (50% saving on those workloads).
- **Savings Plans** require effectively always-on (≥700 h/month) *and* >60%
  steady utilization to justify a commitment.
- **Reserved Instances** require always-on production stateful resources
  (RDS/ElastiCache/OpenSearch).
- **Graviton** only targets `x86` instances; unknown/locked families carry a
  higher compatibility risk flag.

## Deduplication

Overlapping recommendations on the same resource (e.g. rightsize vs. Graviton
vs. a commitment) are collapsed so they are **never summed**. Physical changes
(stop-idle, rightsize, graviton, schedule) are mutually exclusive; the
highest-confidence survivor is kept and commitments are re-based against the
reduced footprint.
