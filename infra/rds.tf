# ── DB Subnet Group (cần 2 AZ) ─────────────────────────────────────────────────
resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-db-subnet-group"
  subnet_ids  = aws_subnet.private_data[*].id
  description = "SOSFlow RDS subnet group (private data subnets)"
}

# ── RDS PostgreSQL ─────────────────────────────────────────────────────────────
resource "aws_db_instance" "postgres" {
  identifier = "${var.project_name}-postgres"

  # Engine
  engine               = "postgres"
  engine_version       = "16"
  instance_class       = var.db_instance_class

  # Storage
  allocated_storage     = 20
  max_allocated_storage = 100  # Auto-scaling storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Credentials
  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Backup / Maintenance
  backup_retention_period = 1    # 1 ngày backup (hackathon)
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  # Performance
  parameter_group_name = "default.postgres16"

  # Lifecycle
  skip_final_snapshot       = true   # Hackathon: xóa không cần snapshot
  deletion_protection       = false
  apply_immediately         = true

  depends_on = [aws_secretsmanager_secret_version.db_password]

  tags = { Name = "${var.project_name}-rds-postgres" }
}
