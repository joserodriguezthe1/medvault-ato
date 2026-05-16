# ==========================================================================
# Terraform settings and AWS provider configuration
# Kept in a separate file from the resources for clarity.
# ==========================================================================

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      System         = "MedVault"
      ManagedBy      = "Terraform"
      Categorization = "FedRAMP-Moderate"
    }
  }
}
