variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-1"
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
  default     = "197826770971"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "sosflow"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "demo"
}

# ── Network ────────────────────────────────────────────────────────────────────
variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AZs to use (ALB requires 2+)"
  type        = list(string)
  default     = ["ap-southeast-1a", "ap-southeast-1b"]
}

# ── EC2 ────────────────────────────────────────────────────────────────────────
variable "ec2_instance_type" {
  description = "EC2 instance type for backend"
  type        = string
  default     = "t3.small"
}

variable "ec2_key_pair_name" {
  description = "EC2 key pair for SSH (optional, để trống nếu dùng SSM)"
  type        = string
  default     = ""
}

# ── RDS ────────────────────────────────────────────────────────────────────────
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "sosflow"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "sosflow"
}

# ── ElastiCache ────────────────────────────────────────────────────────────────
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

# ── AI / Bedrock ────────────────────────────────────────────────────────────────
variable "bedrock_model_id" {
  description = "Bedrock model ID"
  type        = string
  default     = "amazon.nova-lite-v1:0"
}

variable "bedrock_inference_profile_arn" {
  description = "Bedrock inference profile ARN"
  type        = string
  default     = "arn:aws:bedrock:ap-southeast-1:197826770971:inference-profile/apac.amazon.nova-lite-v1:0"
}

variable "bedrock_timeout_seconds" {
  description = "Bedrock call timeout"
  type        = number
  default     = 12
}

variable "bedrock_max_retries" {
  description = "Bedrock max retries"
  type        = number
  default     = 2
}

variable "ai_fallback_enabled" {
  description = "Enable mock fallback when Bedrock fails"
  type        = bool
  default     = true
}

# ── App config ────────────────────────────────────────────────────────────────
variable "demo_mode" {
  description = "Enable demo mode (control panel, auto seed)"
  type        = bool
  default     = true
}

variable "demo_token" {
  description = "Demo mode access token"
  type        = string
  default     = "sosflow-demo-2026"
  sensitive   = true
}

variable "seed_on_startup" {
  description = "Seed initial data on startup"
  type        = bool
  default     = true
}
