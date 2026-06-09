variable "name_prefix" {
  description = "Prefix for all resource names (e.g. ep-foundry-dev)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "public_subnet_cidrs" {
  description = "List of CIDR blocks for public subnets (one per AZ, minimum 2)"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "List of CIDR blocks for private subnets (one per AZ, minimum 2)"
  type        = list(string)
}

variable "availability_zones" {
  description = "List of availability zones to deploy subnets into (must match subnet CIDR list lengths)"
  type        = list(string)
}

variable "tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default     = {}
}
