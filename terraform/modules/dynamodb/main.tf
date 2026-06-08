# DynamoDB Table: Executions
resource "aws_dynamodb_table" "executions" {
  name           = "${var.name_prefix}-executions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "execution_id"

  attribute {
    name = "execution_id"
    type = "S"
  }

  attribute {
    name = "slack_channel"
    type = "S"
  }

  attribute {
    name = "project_name"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "service_request_id"
    type = "S"
  }

  # GSI for querying by Slack channel
  global_secondary_index {
    name            = "slack-channel-index"
    hash_key        = "slack_channel"
    projection_type = "ALL"
  }

  # GSI for querying by project name
  global_secondary_index {
    name            = "project-name-index"
    hash_key        = "project_name"
    projection_type = "ALL"
  }

  # GSI for querying by status
  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
  }

  # GSI for querying by Service Request ID
  global_secondary_index {
    name            = "service-request-id-index"
    hash_key        = "service_request_id"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = var.tags
}

# DynamoDB Table: Execution Logs
resource "aws_dynamodb_table" "execution_logs" {
  name           = "${var.name_prefix}-execution-logs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "execution_id"
  range_key      = "timestamp"

  attribute {
    name = "execution_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "step_name"
    type = "S"
  }

  # GSI for querying logs by step name
  global_secondary_index {
    name            = "step-name-index"
    hash_key        = "step_name"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = var.tags
}
