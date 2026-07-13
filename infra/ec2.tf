# ── Amazon Linux 2023 AMI (latest) ────────────────────────────────────────────
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── EC2 Instance (Backend) ─────────────────────────────────────────────────────
resource "aws_instance" "backend" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.ec2_instance_type
  subnet_id              = aws_subnet.private_app[0].id   # private app subnet (AZ-a)
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  # Key pair SSH (nếu không có → dùng SSM Session Manager)
  key_name = var.ec2_key_pair_name != "" ? var.ec2_key_pair_name : null

  # Storage: 30GB gp3 (nhanh hơn gp2, cùng giá)
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    delete_on_termination = true
    encrypted             = true
  }

  # User data: inject biến Terraform vào script khởi động
  user_data = templatefile("${path.module}/templates/user_data.sh", {
    aws_region                    = var.aws_region
    account_id                    = var.account_id
    ecr_backend_url               = aws_ecr_repository.backend.repository_url
    rds_endpoint                  = aws_db_instance.postgres.endpoint
    redis_host                    = aws_elasticache_cluster.redis.cache_nodes[0].address
    # CORS: ALB URL + wildcard cho CloudFront (CloudFront URL sẽ update qua SSM sau khi tạo xong)
    cors_origins                  = "http://${aws_lb.backend.dns_name},http://localhost:5173"
    bedrock_inference_profile_arn = var.bedrock_inference_profile_arn
    bedrock_model_id              = var.bedrock_model_id
    bedrock_timeout_seconds       = tostring(var.bedrock_timeout_seconds)
    bedrock_max_retries           = tostring(var.bedrock_max_retries)
    ai_fallback_enabled           = tostring(var.ai_fallback_enabled)
    demo_mode                     = tostring(var.demo_mode)
    seed_on_startup               = tostring(var.seed_on_startup)
    project_name                  = var.project_name
  })

  # Chạy startup sau khi RDS, Redis, Secrets Manager đã sẵn sàng
  depends_on = [
    aws_db_instance.postgres,
    aws_elasticache_cluster.redis,
    aws_secretsmanager_secret_version.db_password,
    aws_secretsmanager_secret_version.demo_token,
    aws_ecr_repository.backend,
    aws_nat_gateway.main,
    aws_lb.backend,
  ]

  tags = {
    Name = "${var.project_name}-backend-ec2"
    Role = "backend"
  }

  lifecycle {
    # Thay image mới → chỉ restart container (dùng redeploy script), không rebuild EC2
    ignore_changes = [user_data]
  }
}

# ── CloudWatch Alarm: EC2 CPU cao ─────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "ec2_cpu" {
  alarm_name          = "${var.project_name}-ec2-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "EC2 CPU > 80% trong 4 phút"

  dimensions = {
    InstanceId = aws_instance.backend.id
  }
}
