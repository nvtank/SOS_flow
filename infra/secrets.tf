# ── Random password cho RDS ────────────────────────────────────────────────────
resource "random_password" "db_password" {
  length  = 32
  special = false  # Tránh ký tự đặc biệt trong connection string
}

# ── Secrets Manager: DB Password ──────────────────────────────────────────────
resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.project_name}/db-password"
  description             = "SOSFlow RDS PostgreSQL password"
  recovery_window_in_days = 0  # Xóa ngay không cần 30 ngày (hackathon)
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

# ── Secrets Manager: Demo Token ───────────────────────────────────────────────
resource "aws_secretsmanager_secret" "demo_token" {
  name                    = "${var.project_name}/demo-token"
  description             = "SOSFlow demo access token"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "demo_token" {
  secret_id     = aws_secretsmanager_secret.demo_token.id
  secret_string = var.demo_token
}
