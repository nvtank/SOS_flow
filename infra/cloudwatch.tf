# ── CloudWatch Log Groups ─────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "ec2_startup" {
  name              = "/sosflow/ec2/startup"
  retention_in_days = 7

  tags = { Name = "${var.project_name}-logs-startup" }
}

resource "aws_cloudwatch_log_group" "backend_app" {
  name              = "/sosflow/backend/app"
  retention_in_days = 14

  tags = { Name = "${var.project_name}-logs-backend" }
}

# ── ALB Request Count Alarm ───────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${var.project_name}-alb-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Backend trả về >10 lỗi 5xx trong 1 phút"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.backend.arn_suffix
  }
}

# ── ALB Unhealthy Hosts Alarm ─────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "alb_unhealthy" {
  alarm_name          = "${var.project_name}-alb-unhealthy-hosts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "EC2 backend bị ALB mark unhealthy"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TargetGroup  = aws_lb_target_group.backend.arn_suffix
    LoadBalancer = aws_lb.backend.arn_suffix
  }
}
