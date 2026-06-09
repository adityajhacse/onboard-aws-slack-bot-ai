variable "project" {
  description = "Project name used to namespace all resource names."
  type        = string
}

variable "secret_arn" {
  description = "ARN of the Secrets Manager secret the execution role must be allowed to read."
  type        = string
}
