terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # State lưu local cho hackathon — không cần S3 backend
  # Nếu muốn share state: uncomment và tạo S3 bucket trước
  # backend "s3" {
  #   bucket = "sosflow-tfstate-197826770971"
  #   key    = "sosflow/terraform.tfstate"
  #   region = "ap-southeast-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
