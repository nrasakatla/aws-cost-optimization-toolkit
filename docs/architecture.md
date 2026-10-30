# Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          DATA COLLECTION LAYER                           │
│   Python + boto3 (optional, read-only, opt-in only — NOT used by demo)   │
│                                                                          │
│   providers/                                                             │
│     base.py        Provider ABC + registry                               │
│     sample.py      SYNTHETIC deterministic multi-account provider (demo) │
│     (live boto3 collectors: stub/opt-in, never called in tests)          │
│                                                                          │
│   Output: list[Resource] — normalized inventory, versioned JSON          │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    │  list[Resource]
┌───────────────────────────────────▼──────────────────────────────────────┐
│                       RECOMMENDATION ENGINE (pure, no I/O)               │
│                                                                          │
│   engine/rules/*     one generator per action type:                      │
│                      rightsize · idle · schedule · eks · ebs             │
│                      savings_plans · reserved_instances · graviton       │
│                      nat · storage                                       │
│   engine/classify.py effort / risk / restart / rollback / confidence     │
│   engine/dedupe.py   collapse overlapping recs (no double-count)         │
│   engine/savings.py  gross → actionable → approved → realized            │
│                                                                          │
│   Every dollar figure computed from documented assumptions + evidence.   │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    │  list[Recommendation]
┌───────────────────────────────────▼──────────────────────────────────────┐
│                         DASHBOARD LAYER (Streamlit)                      │
│   Dark theme · original UI · offline · synthetic data only               │
│                                                                          │
│   Global filters: account, region, environment, resource type, action,   │
│                   effort, risk, restart, rollback, status, $ threshold    │
│   KPIs + charts: before/after, by action, by account, by resource type,  │
│                  top recommendations                                     │
│   Searchable table + CSV export                                          │
│   Prominent simulation disclaimer                                        │
└──────────────────────────────────────────────────────────────────────────┘
```

## Data flow

1. `SyntheticProvider(seed=42)` produces a deterministic, multi-account,
   multi-region resource inventory (EC2, EBS, RDS, EKS, ELB, NAT, ElastiCache,
   OpenSearch, Lambda, S3, CloudWatch).
2. Each rule inspects resources and emits candidate `Recommendation`s **only
   when the synthetic evidence supports them** (missing metrics block, never
   imply zero).
3. `classify` tags effort/risk/restart/rollback/confidence; `dedupe` collapses
   overlapping actions on the same resource; `savings` tracks the four-stage
   pipeline.
4. The dashboard renders the post-dedupe recommendations with interactive
   filters and CSV export.

## Key design principles

- **Pure engine:** the recommendation/savings/dedupe logic is 100% I/O-free and
  unit-tested without AWS.
- **Synthetic-first:** the demo path never constructs a boto3 client; live
  collection requires explicit double opt-in.
- **Honest accounting:** estimated savings are never labeled "verified"; the
  dashboard carries a prominent simulation disclaimer.
- **No double-counting:** overlapping recommendations are collapsed via
  precedence + rebasing, never summed.
