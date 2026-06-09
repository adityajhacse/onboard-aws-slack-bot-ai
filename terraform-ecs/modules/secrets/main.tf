# ---------------------------------------------------------------------------
# AWS Secrets Manager — creates the secret container only.
# Secret values (key/value pairs) are managed separately and not set here.
# ECS resolves each JSON key individually at task launch via the secrets[]
# block in the task definition (see modules/ecs/main.tf).
# ---------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "this" {
  name                    = "${var.project}/secrets"
  description             = "Sensitive credentials for the ${var.project} ECS task."
  recovery_window_in_days = 7
}
