terraform {
  required_version = ">= 1.13.5, < 2.0"
  required_providers {
    aws = {
      source = "hashicorp/aws", version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Projet = var.nom, GerePar = "Terraform"
    }
  }
}

data "aws_caller_identity" "compte" {
}

data "aws_availability_zones" "disponibles" {
  state = "available"
}

locals {
  zones   = slice(data.aws_availability_zones.disponibles.names, 0, 2)
  prefixe = "${var.nom}-${data.aws_caller_identity.compte.account_id}"
}
