# ==========================================================================
# MedVault - Step 1
# Encrypted, logged, versioned S3 bucket for storing public-health reports.
#
# Controls satisfied by this file:
#   SC-13  Cryptographic Protection   (KMS customer-managed key + bucket SSE)
#   AU-2   Event Logging              (S3 server access logging enabled)
#   CM-6   Configuration Settings     (public access blocked, versioning,
#                                      TLS-only bucket policy)
# ==========================================================================

# ----- SC-13: Customer-managed KMS key for bucket encryption -----------------
resource "aws_kms_key" "reports" {
  description             = "MedVault reports bucket encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true   # SC-12 - annual key rotation
  tags = {
    Control = "SC-13"
    System  = "MedVault"
  }
}

resource "aws_kms_alias" "reports" {
  name          = "alias/medvault-reports"
  target_key_id = aws_kms_key.reports.key_id
}

# ----- The primary data bucket -----------------------------------------------
resource "aws_s3_bucket" "reports" {
  bucket = "medvault-reports-${var.environment}"

  tags = {
    System         = "MedVault"
    Environment    = var.environment
    DataClass      = "CUI-HLTH"
    Categorization = "FedRAMP-Moderate"
  }
}

# SC-13: Server-side encryption with our customer-managed KMS key
resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.reports.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# CM-6: Block ALL public access (the four-flag pattern)
resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CM-6: Versioning protects against accidental + malicious deletion
resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id
  versioning_configuration {
    status = "Enabled"
  }
}

# CM-6 / SC-8: Bucket policy enforces TLS-only access
resource "aws_s3_bucket_policy" "reports_tls_only" {
  bucket = aws_s3_bucket.reports.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource = [
        aws_s3_bucket.reports.arn,
        "${aws_s3_bucket.reports.arn}/*",
      ]
      Condition = {
        Bool = { "aws:SecureTransport" = "false" }
      }
    }]
  })
}

# ----- AU-2: Server access logging -------------------------------------------
# Logs go to a SEPARATE bucket so log integrity isn't dependent on the
# bucket being audited. The logging bucket itself is also encrypted.

resource "aws_s3_bucket" "access_logs" {
  bucket = "medvault-access-logs-${var.environment}"
  tags = {
    System  = "MedVault"
    Purpose = "Access logs (AU-2 evidence)"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"   # S3-managed key is sufficient for log bucket
    }
  }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket                  = aws_s3_bucket.access_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Point the reports bucket access logging at the logs bucket
resource "aws_s3_bucket_logging" "reports" {
  bucket        = aws_s3_bucket.reports.id
  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "reports/"
}

# ----- Inputs ----------------------------------------------------------------
variable "environment" {
  type        = string
  description = "Deployment environment (dev / staging / prod)"
  default     = "dev"
}

# ----- Outputs (used later by app & for SSP evidence) ------------------------
output "reports_bucket_name" {
  value = aws_s3_bucket.reports.id
}

output "reports_kms_key_arn" {
  value = aws_kms_key.reports.arn
}
