# Control Implementation Matrix — MedVault

Maps each implemented FedRAMP Moderate control to the technical component(s) satisfying it, the code artifact, the pipeline check, and the OSCAL artifact.

## Implemented Controls

| Control | Title | Implementation | Code | Pipeline Evidence |
|---|---|---|---|---|
| AC-6 | Least Privilege | Resource-scoped IAM policy | `docs/iam-policy.json` | One-time configuration |
| AU-2 | Event Logging | S3 server access logging to separate bucket | `infrastructure/s3-bucket.tf` | Checkov CKV_AWS_
