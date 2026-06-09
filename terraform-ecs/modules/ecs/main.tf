# ---------------------------------------------------------------------------
# Subnet lookup — discover private subnets tagged project=ep-foundry that
# belong to the VPC wired into this module, without hard-coding IDs.
# ---------------------------------------------------------------------------

data "aws_subnets" "private" {
  filter {
    name   = "tag:project"
    values = ["ep-foundry"]
  }
}

# ---------------------------------------------------------------------------
# CloudWatch Log Group
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${var.project}"
  retention_in_days = var.log_retention_days
}

# ---------------------------------------------------------------------------
# Security Group
# The Slack bot uses Socket Mode — it dials OUT to Slack and AWS APIs.
# No inbound ports are needed.
# ---------------------------------------------------------------------------

resource "aws_security_group" "task" {
  name        = "${var.project}-ecs-task-sg"
  description = "Security group for ${var.project} ECS Fargate tasks."
  vpc_id      = var.vpc_id

  egress {
    description = "Allow all outbound traffic (Slack, AWS APIs, OpenAI gateway)."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------------------------------------------------------------------------
# ECS Cluster
# ---------------------------------------------------------------------------

resource "aws_ecs_cluster" "this" {
  name = var.project

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }
}

# ---------------------------------------------------------------------------
# ECS Task Definition
# ---------------------------------------------------------------------------

resource "aws_ecs_task_definition" "this" {
  family                   = "${var.project}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = var.service_name
      image     = var.ecr_image_uri
      essential = true

      # ---- All config and secrets pulled from Secrets Manager at launch ----
      # Format: "<secret-arn>:<json-key>::"
      environment = []

      secrets = [
        { name = "SLACK_BOT_TOKEN",                 valueFrom = "${var.secret_arn}:SLACK_BOT_TOKEN::" },
        { name = "SLACK_APP_TOKEN",                 valueFrom = "${var.secret_arn}:SLACK_APP_TOKEN::" },
        { name = "HCP_TERRAFORM_TOKEN",             valueFrom = "${var.secret_arn}:HCP_TERRAFORM_TOKEN::" },
        { name = "GITHUB_TOKEN",                    valueFrom = "${var.secret_arn}:GITHUB_TOKEN::" },
        { name = "OPENAI_API_KEY",                  valueFrom = "${var.secret_arn}:OPENAI_API_KEY::" },
        { name = "AI_API_KEY",                      valueFrom = "${var.secret_arn}:AI_API_KEY::" },
        { name = "DET_ALLOWED_CHANNELS",            valueFrom = "${var.secret_arn}:DET_ALLOWED_CHANNELS::" },
        { name = "HCP_TERRAFORM_ORG",               valueFrom = "${var.secret_arn}:HCP_TERRAFORM_ORG::" },
        { name = "HCP_TERRAFORM_VCS_OAUTH_TOKEN_ID",valueFrom = "${var.secret_arn}:HCP_TERRAFORM_VCS_OAUTH_TOKEN_ID::" },
        { name = "GITHUB_OWNER",                    valueFrom = "${var.secret_arn}:GITHUB_OWNER::" },
        { name = "GITHUB_REPO",                     valueFrom = "${var.secret_arn}:GITHUB_REPO::" },
        { name = "GITHUB_BASE_BRANCH",              valueFrom = "${var.secret_arn}:GITHUB_BASE_BRANCH::" },
        { name = "GITHUB_FILE_PATH",                valueFrom = "${var.secret_arn}:GITHUB_FILE_PATH::" },
        { name = "AI_PROVIDER",                     valueFrom = "${var.secret_arn}:AI_PROVIDER::" },
        { name = "OPENAI_BASE_URL",                 valueFrom = "${var.secret_arn}:OPENAI_BASE_URL::" },
        { name = "AI_MODEL",                        valueFrom = "${var.secret_arn}:AI_MODEL::" },
        { name = "AI_SSL_VERIFY",                   valueFrom = "${var.secret_arn}:AI_SSL_VERIFY::" },
        { name = "DET_DRY_RUN",                     valueFrom = "${var.secret_arn}:DET_DRY_RUN::" },
        { name = "API_GATEWAY_ENDPOINT",            valueFrom = "${var.secret_arn}:API_GATEWAY_ENDPOINT::" },
        { name = "STATUS_API_URL",                  valueFrom = "${var.secret_arn}:STATUS_API_URL::" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.this.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import sys; sys.exit(0)\""]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------
# ECS Service
# ---------------------------------------------------------------------------

resource "aws_ecs_service" "this" {
  name            = var.service_name
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  force_new_deployment = true

  network_configuration {
    subnets          = data.aws_subnets.private.ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = var.assign_public_ip
  }

  depends_on = [aws_cloudwatch_log_group.this]

  lifecycle {
    ignore_changes = [desired_count]
  }
}
