terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment and fill in to use a remote S3 backend:
  # backend "s3" {
  #   bucket         = "833608842610-terraform-state"
  #   key            = "ep-foundry-slack/terraform.tfstate"
  #   region         = "us-west-2"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

locals {
  project      = "ep-foundry-slack"
  service_name = "slack-bot"
  name_prefix  = "${local.project}-${var.environment}"

  common_tags = {
    Project     = local.project
    project     = "ep-foundry"
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  tags = local.common_tags

  # When create_vpc=true, pull networking from the VPC module; otherwise use caller-supplied values.
  resolved_vpc_id    = var.create_vpc ? module.vpc[0].vpc_id : var.vpc_id
  resolved_subnet_ids = var.create_vpc ? module.vpc[0].private_subnet_ids : var.subnet_ids
}


# ---------------------------------------------------------------------------
# VPC (conditional — sandbox only; ADR-013)
# ---------------------------------------------------------------------------

module "vpc" {
  count  = var.create_vpc ? 1 : 0
  source = "./modules/vpc"

  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  availability_zones   = ["${var.aws_region}a", "${var.aws_region}b"]
  tags                 = local.tags
}


# ---------------------------------------------------------------------------
# Module: secrets
# Creates the single JSON secret in AWS Secrets Manager.
# ---------------------------------------------------------------------------

module "secrets" {
  source = "./modules/secrets"

  project = local.project
}

# ---------------------------------------------------------------------------
# Module: iam
# Creates the ECS execution role (ECR + logs + Secrets Manager) and task role.
# ---------------------------------------------------------------------------

module "iam" {
  source = "./modules/iam"

  project    = local.project
  secret_arn = module.secrets.secret_arn
}

# ---------------------------------------------------------------------------
# Module: ecs
# Creates the cluster, task definition, service, log group and security group.
# ---------------------------------------------------------------------------

module "ecs" {
  source = "./modules/ecs"

  depends_on = [module.vpc]

  project      = local.project
  service_name = local.service_name
  aws_region   = var.aws_region

  # Networking — resolved dynamically from vpc module when create_vpc=true
  vpc_id           = local.resolved_vpc_id
  subnet_ids       = local.resolved_subnet_ids
  assign_public_ip = var.assign_public_ip

  # Container
  ecr_image_uri      = var.ecr_image_uri
  task_cpu           = var.task_cpu
  task_memory        = var.task_memory
  desired_count      = var.desired_count
  log_retention_days = var.log_retention_days

  # IAM — wired from the iam module
  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn

  # Secrets — wired from the secrets module
  secret_arn = module.secrets.secret_arn
}
