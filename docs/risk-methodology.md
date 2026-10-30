# Operational Risk Methodology

Every recommendation carries an **operational risk** rating (`Low` / `Medium` /
`High`) and a **restart requirement** and **rollback feasibility** flag. These
are not arbitrary: each is derived from the recommendation's action type, the
resource family, and (where relevant) evidence completeness.

## Risk assignment rules

| Action | Baseline risk | Notes |
|---|---|---|
| Stop Idle | Low | Reversible; resource already idle |
| EBS Upgrade (gp2→gp3) | Low | Live volume modification, no downtime |
| EBS snapshot cleanup | Low | Delete-only, recoverable from source |
| Purchase Savings Plans | Low | Financial commitment; no infra change |
| Purchase Reserved Instances | Low | Financial commitment; no infra change |
| NAT Gateway Optimize | Low | Routing change; easily reverted |
| Storage Retention (S3 lifecycle) | Low | Config change; reversible |
| Schedule non-prod | Medium | Availability impact on non-prod users |
| EKS Optimize | Medium | Node-group scaling; watch PDBs |
| Rightsize (EC2) | Medium | Restart required; ensure capacity |
| Rightsize (RDS) | **High** | DB resize → downtime window; multi-AZ recommended |
| Migrate to Graviton | **High** (x86-locked) / Medium | Binary/arch compatibility must be verified first |

## Evidence confidence

Each recommendation carries `evidence_confidence ∈ [0, 1]`, computed as the
ratio of *measured* signals to total signal slots. A recommendation is emitted
**only** when the required signals are present — a missing metric blocks the
recommendation rather than being treated as zero usage. Lower confidence does
not block emission, but it is surfaced in the table so a reviewer can
prioritize higher-confidence actions first.

## Why not just "keep the largest saving"?

Deduplication uses **precedence + rebasing**, not "keep the largest":

1. Physical changes (Stop Idle, Rightsize, Graviton, Schedule) are mutually
   exclusive per resource — you cannot rightsize *and* fully migrate the same
   instance. The highest-confidence physical change survives.
2. Commitments (Savings Plans, Reserved Instances) apply to the *reduced* base
   after a physical change, so they are rebased (scaled) rather than stacked on
   the pre-change cost.

This guarantees overlapping recommendations are never summed.
