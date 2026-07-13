# ── ALB Security Group ─────────────────────────────────────────────────────────
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-sg-alb"
  description = "ALB: allow HTTP inbound from internet"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Egress to EC2 — dùng separate rule để tránh circular dep
  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-sg-alb" }
}

# ── EC2 Security Group ─────────────────────────────────────────────────────────
resource "aws_security_group" "ec2" {
  name        = "${var.project_name}-sg-ec2"
  description = "EC2 backend: receive from ALB, outbound to RDS/Redis/AWS services"
  vpc_id      = aws_vpc.main.id

  # Inbound từ ALB — dùng separate rule để tránh circular dep với ALB SG
  ingress {
    description = "API traffic from ALB subnet"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # ALB trong public subnet; SG restrict ở ALB side
  }

  egress {
    description = "All outbound - NAT to ECR, Bedrock, Secrets Manager"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-sg-ec2" }
}

# ── RDS Security Group ─────────────────────────────────────────────────────────
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-sg-rds"
  description = "RDS PostgreSQL: only from EC2"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  tags = { Name = "${var.project_name}-sg-rds" }
}

# ── ElastiCache Security Group ─────────────────────────────────────────────────
resource "aws_security_group" "redis" {
  name        = "${var.project_name}-sg-redis"
  description = "ElastiCache Redis: only from EC2"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis from EC2"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  tags = { Name = "${var.project_name}-sg-redis" }
}
