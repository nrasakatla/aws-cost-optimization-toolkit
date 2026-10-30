# Security & Limitations

## Security considerations

- **Synthetic by default.** The demo and the entire test suite run on the
  `SyntheticProvider`; no boto3 client is ever constructed on the demo path.
  A test (`test_offline_no_aws_import_executed`) fails the suite if `boto3.client`
  is called during analysis.
- **Double opt-in for live collection.** The `collect_aws.py` script refuses to
  run unless `COSTTK_COLLECTOR=live` + `COSTTK_READ_ONLY=1` are set *and*
  `--yes-i-know` is passed on the CLI.
- **Read-only IAM only.** `data/iam-policy.json` scopes to descriptive/get APIs
  (`ec2:Describe*`, `ce:Get*`, `compute-optimizer:Get*`, `organizations:List*`,
  etc.). No write/modify/delete permission appears anywhere.
- **No secrets in the repo.** `.env`, `*.pem`, and `credentials/` are
  gitignored. The synthetic account IDs (`1000000000xx`) are fictional.
- **No confidential data.** The model contains zero real billing, usage, or
  account data — everything is seeded and deterministic.

## Known limitations

- **Estimates, not realized savings.** All savings are *modeled* from documented
  pricing assumptions. They are labeled "ESTIMATED" and are never presented as
  verified billing reductions. The dashboard carries an explicit simulation
  disclaimer.
- **Static snapshot.** The synthetic dataset is a single point-in-time
  snapshot. There is no time-series history of recommendations (simulated or
  otherwise) — `savings over time` trends are out of scope for this version.
- **Pricing assumptions are synthetic.** Unit prices (e.g. `$4.20/vCPU-month`)
  are plausible but not AWS-quoted; they exist to make the scenario realistic,
  not authoritative.
- **Live collectors are stubs.** The boto3 adapters are documented as
  *incomplete* (stub/guard only). No live AWS API is implemented, by design.
- **No multi-AZ / data-loss modelling.** Resource `multi_az` and dependency
  attributes are captured but not yet used to gate recommendations.
- **No org-level tag inheritance.** The `FinOpsException` tag concept from the
  reference is not implemented; filtering is by account/region/env/type only.
