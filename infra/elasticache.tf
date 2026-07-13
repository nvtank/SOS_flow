# ── ElastiCache Subnet Group ───────────────────────────────────────────────────
resource "aws_elasticache_subnet_group" "main" {
  name        = "${var.project_name}-redis-subnet-group"
  subnet_ids  = aws_subnet.private_data[*].id
  description = "SOSFlow Redis subnet group"
}

# ── ElastiCache Redis ──────────────────────────────────────────────────────────
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379

  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  # Maintenance
  maintenance_window   = "sun:05:00-sun:06:00"

  tags = { Name = "${var.project_name}-redis" }
}
