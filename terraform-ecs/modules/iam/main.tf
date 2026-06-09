# ---------------------------------------------------------------------------
# Shared assume-role policy for ECS tasks
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# ---------------------------------------------------------------------------
# ECS Task Execution Role
# Used by the ECS agent (not the app) to:
#   - Pull the container image from ECR
#   - Write logs to CloudWatch
#   - Fetch secret values from Secrets Manager at task launch
# ---------------------------------------------------------------------------

resource "aws_iam_role" "execution" {
  name               = "${var.project}-ecs-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "secrets_read" {
  statement {
    sid    = "ReadAppSecret"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = ["${var.secret_arn}*"]
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  name   = "SecretsManagerAccess"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.secrets_read.json
}

# ---------------------------------------------------------------------------
# ECS Task Role
# Used by the running application container.
# Add additional statements here if the app needs to call AWS APIs directly
# (e.g. STS, S3, SQS).  Currently empty by design.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "task" {
  name               = "${var.project}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}
