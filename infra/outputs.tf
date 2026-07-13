output "alb_dns_name" {
  description = "ALB DNS - Backend API endpoint"
  value       = "http://${aws_lb.backend.dns_name}"
}

output "cloudfront_url" {
  description = "CloudFront URL - Frontend"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "frontend_bucket_name" {
  description = "S3 bucket chứa frontend static files"
  value       = aws_s3_bucket.frontend.id
}

output "cloudfront_distribution_id" {
  description = "CloudFront Distribution ID (dùng để invalidate cache)"
  value       = aws_cloudfront_distribution.frontend.id
}

output "ecr_backend_url" {
  description = "ECR backend image URL"
  value       = aws_ecr_repository.backend.repository_url
}

output "ec2_instance_id" {
  description = "EC2 Instance ID (dùng SSM để kết nối)"
  value       = aws_instance.backend.id
}

output "ec2_private_ip" {
  description = "EC2 Private IP"
  value       = aws_instance.backend.private_ip
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = "${aws_elasticache_cluster.redis.cache_nodes[0].address}:${aws_elasticache_cluster.redis.cache_nodes[0].port}"
  sensitive   = true
}

output "db_password_secret_arn" {
  description = "ARN của Secrets Manager secret chứa DB password"
  value       = aws_secretsmanager_secret.db_password.arn
}

output "deploy_summary" {
  description = "Tóm tắt endpoint sau khi deploy xong"
  value = <<-EOT
    ════════════════════════════════════════════
    SOSFlow đã deploy thành công!
    ────────────────────────────────────────────
    🌐 Frontend : https://${aws_cloudfront_distribution.frontend.domain_name}
    ⚙️  Backend  : http://${aws_lb.backend.dns_name}
    📋 API Docs : http://${aws_lb.backend.dns_name}/docs
    🖥️  EC2 ID   : ${aws_instance.backend.id}  (SSM để SSH)
    ════════════════════════════════════════════
  EOT
}
