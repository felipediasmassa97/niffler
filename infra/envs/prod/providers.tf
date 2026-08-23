terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Hop 1 (SSO -> niffler-infra-role) happens via the "niffler-infra" CLI profile.
# Hop 2 (niffler-infra-role -> niffler-infra-execution-role) happens here, so every
# resource operation this provider performs runs as niffler-infra-execution-role, never
# as the raw admin SSO session or niffler-infra-role directly.
provider "aws" {
  region  = var.region
  profile = "niffler-infra"

  assume_role {
    role_arn     = "arn:aws:iam::${var.account_id}:role/niffler-infra-execution-role"
    session_name = "niffler-terraform-${var.environment}"
  }
}
