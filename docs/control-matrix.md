# Control Implementation Matrix — MedVault



This document maps each implemented FedRAMP Moderate control to the technical component(s) satisfying it, the code artifact, the pipeline check producing evidence, and the OSCAL artifact capturing the result.



\## Implemented Controls



| Control | Title | Implementation | Code | Pipeline Evidence |

|---|---|---|---|---|

| AC-6 | Least Privilege | Resource-scoped IAM policy for Terraform | `docs/iam-policy.json` | One-time configuration |

| AU-2 | Event Logging | S3 server access logging to separate bucket | `infrastructure/s3-bucket.tf` | Checkov CKV\_AWS\_18 PASS |

| CA-7 | Continuous Monitoring | Pipeline runs on every push, OSCAL per run | `.github/workflows/terraform-scan.yml` | All AR documents in `oscal/assessment-results/` |

| CM-3 | Configuration Change Control | Workflow gate + branch protection | `.github/workflows/terraform-scan.yml` | Failed builds block merges |

| CM-6 | Configuration Settings | Checkov enforces baseline | `.github/workflows/terraform-scan.yml` | Checkov SARIF |

| RA-5 | Vulnerability Monitoring | Checkov for IaC | `.github/workflows/terraform-scan.yml` | Checkov SARIF in GitHub Security tab |

| SA-11 | Developer Security Testing | Security checks in dev pipeline | `.github/workflows/terraform-scan.yml` | Workflow runs |

| SC-13 | Cryptographic Protection | KMS customer-managed key + bucket SSE | `infrastructure/s3-bucket.tf` | Checkov CKV\_AWS\_19 PASS + AWS API confirms |

| SI-2 | Flaw Remediation | Failed Checkov blocks merge | `.github/workflows/terraform-scan.yml` | Workflow gate fires on findings |



\## Known Gaps (Tracked in POA\&M)



Of the 9 Checkov findings produced by the pipeline, 6 are formally tracked in `oscal/poam/medvault-poam.json`:



| Item | Severity | Control | Status | Due |

|---|---|---|---|---|

| POAM-001: KMS key has no explicit policy | High | SC-13 | Open | 2026-06-15 |

| POAM-002: Log bucket lacks versioning | High | AU-9 | Open | 2026-06-01 |

| POAM-003: Log bucket uses AES256 not KMS | Medium | SC-13 | Open | 2026-07-15 |

| POAM-004: No lifecycle policy | Medium | AU-11 | Open | 2026-07-01 |

| POAM-005: No event notifications | Medium | SI-4 | Open | 2026-08-01 |

| POAM-006: No cross-region replication | Low | CP-9 | \*\*Risk Accepted\*\* | N/A |



POAM-006 demonstrates the formal risk-acceptance workflow: a documented decision with compensating controls (versioning, separate-account backup), accepted by the AO.



\## Future Scope (Planned)



| Control | Planned Implementation |

|---|---|

| AC-3 | IAM + Kubernetes RBAC + security groups |

| AU-11 | S3 lifecycle policy (1 year online + 6 years Glacier) |

| AU-12 | CloudTrail organization-trail + flow logs |

| CM-7 | Distroless container, minimal package surface |

| CM-8 | SBOM (Syft) attached to container |

| SC-7 | VPC + security groups + Kyverno network policies |

| SI-4 | GuardDuty + Falco runtime monitoring |

| SI-7 | Cosign keyless signing + verification |

| SR-3 | Pinned base image digest |

| SR-4 | Cosign provenance via GitHub OIDC |

