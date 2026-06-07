# DynamoDB Table for Service Records and Execution Tracking
resource "aws_dynamodb_table" "executions" {
  name           = "${local.name_prefix}-executions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "execution_id"

  # Primary key
  attribute {
    name = "execution_id"
    type = "S"
  }

  # GSI attributes
  attribute {
    name = "slack_channel"
    type = "S"
  }

  attribute {
    name = "created_at"
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

  # GSI for querying by Slack channel (sorted by creation time)
  global_secondary_index {
    name            = "slack-channel-index"
    hash_key        = "slack_channel"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # GSI for querying by project name
  global_secondary_index {
    name            = "project-name-index"
    hash_key        = "project_name"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # GSI for querying by status (to find running/failed jobs)
  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup after 90 days
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  # Enable streams for change data capture
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = {
    Name        = "${local.name_prefix}-executions"
    Description = "Service records and job status for DET onboarding"
  }
}

# DynamoDB Table for Step-by-Step Execution Logs
resource "aws_dynamodb_table" "execution_logs" {
  name           = "${local.name_prefix}-execution-logs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "execution_id"
  range_key      = "timestamp"

  attribute {
    name = "execution_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
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

  tags = {
    Name        = "${local.name_prefix}-execution-logs"
    Description = "Detailed step-by-step execution logs"
  }
}

# CloudWatch Alarms for DynamoDB
resource "aws_cloudwatch_metric_alarm" "dynamodb_read_throttle" {
  alarm_name          = "${local.name_prefix}-dynamodb-read-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors DynamoDB read throttle events"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.executions.name
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_write_throttle" {
  alarm_name          = "${local.name_prefix}-dynamodb-write-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors DynamoDB write throttle events"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.executions.name
  }
}
