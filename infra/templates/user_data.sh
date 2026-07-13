#!/bin/bash
# SOSFlow Backend EC2 User Data Script
# Chạy lần đầu khi EC2 khởi động

set -euo pipefail
exec > >(tee /var/log/sosflow-startup.log) 2>&1

echo "=== SOSFlow EC2 Startup $(date) ==="

AWS_REGION="${aws_region}"
ACCOUNT_ID="${account_id}"
ECR_URL="${ecr_backend_url}"
RDS_ENDPOINT="${rds_endpoint}"
REDIS_HOST="${redis_host}"
CORS_ORIGINS="${cors_origins}"
BEDROCK_ARN="${bedrock_inference_profile_arn}"
BEDROCK_MODEL="${bedrock_model_id}"
BEDROCK_TIMEOUT="${bedrock_timeout_seconds}"
BEDROCK_RETRIES="${bedrock_max_retries}"
AI_FALLBACK="${ai_fallback_enabled}"
DEMO_MODE="${demo_mode}"
SEED_ON_STARTUP="${seed_on_startup}"
PROJECT="${project_name}"

# ── 1. Cài đặt packages ───────────────────────────────────────────────────────
echo "[1/6] Installing packages..."
dnf update -y
dnf install -y docker aws-cli jq
systemctl start docker
systemctl enable docker

# ── 2. Cài CloudWatch Agent ───────────────────────────────────────────────────
echo "[2/6] Installing CloudWatch Agent..."
dnf install -y amazon-cloudwatch-agent

cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<'CWEOF'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/sosflow-startup.log",
            "log_group_name": "/sosflow/ec2/startup",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/sosflow-backend.log",
            "log_group_name": "/sosflow/backend/app",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
CWEOF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# ── 3. Lấy secrets từ Secrets Manager ────────────────────────────────────────
echo "[3/6] Fetching secrets from Secrets Manager..."
DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id "$PROJECT/db-password" \
  --region "$AWS_REGION" \
  --query SecretString \
  --output text)

DEMO_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id "$PROJECT/demo-token" \
  --region "$AWS_REGION" \
  --query SecretString \
  --output text)

# ── 4. Login ECR và pull image ────────────────────────────────────────────────
echo "[4/6] Logging into ECR and pulling image..."

# Retry login (phòng trường hợp ECR chưa sẵn sàng)
for i in 1 2 3 4 5; do
  if aws ecr get-login-password --region "$AWS_REGION" \
    | docker login --username AWS --password-stdin "$ECR_URL"; then
    echo "ECR login successful"
    break
  fi
  echo "ECR login attempt $i failed, retrying in 15s..."
  sleep 15
done

# Pull image (retry nếu image chưa push)
for i in 1 2 3 4 5 6; do
  if docker pull "$ECR_URL:latest"; then
    echo "Image pulled successfully"
    break
  fi
  echo "Image pull attempt $i failed, retrying in 30s..."
  sleep 30
done

# ── 5. Chạy backend container ─────────────────────────────────────────────────
echo "[5/6] Starting backend container..."

# Stop existing container nếu có (redeploy)
docker stop sosflow-backend 2>/dev/null || true
docker rm sosflow-backend 2>/dev/null || true

docker run -d \
  --name sosflow-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  -e "DATABASE_URL=postgresql+psycopg2://$${DB_PASSWORD//@/%40}@$RDS_ENDPOINT/sosflow" \
  -e "CORS_ORIGINS=$CORS_ORIGINS" \
  -e "PRIORITY_RULES_PATH=/config/priority-rules.yaml" \
  -e "AI_PROVIDER=bedrock" \
  -e "AWS_REGION=$AWS_REGION" \
  -e "BEDROCK_INFERENCE_PROFILE_ARN=$BEDROCK_ARN" \
  -e "BEDROCK_MODEL_ID=$BEDROCK_MODEL" \
  -e "BEDROCK_TIMEOUT_SECONDS=$BEDROCK_TIMEOUT" \
  -e "BEDROCK_MAX_RETRIES=$BEDROCK_RETRIES" \
  -e "AI_FALLBACK_ENABLED=$AI_FALLBACK" \
  -e "DEMO_MODE=$DEMO_MODE" \
  -e "DEMO_TOKEN=$DEMO_TOKEN" \
  -e "SEED_ON_STARTUP=$SEED_ON_STARTUP" \
  "$ECR_URL:latest" \
  2>&1 | tee -a /var/log/sosflow-backend.log

# ── 6. Tạo script redeploy để dùng sau ───────────────────────────────────────
echo "[6/6] Creating redeploy script..."
cat > /usr/local/bin/sosflow-redeploy.sh <<REDEPLOY
#!/bin/bash
# Chạy script này để cập nhật image khi push ECR mới
set -e
echo "Redeploying SOSFlow backend..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL
docker pull $ECR_URL:latest
docker stop sosflow-backend && docker rm sosflow-backend
# Re-run với cùng env vars
docker run -d \\
  --name sosflow-backend \\
  --restart unless-stopped \\
  -p 8000:8000 \\
  --env-file /etc/sosflow/env \\
  $ECR_URL:latest
echo "Redeploy complete!"
docker logs --tail 20 sosflow-backend
REDEPLOY
chmod +x /usr/local/bin/sosflow-redeploy.sh

# ── Lưu env file để redeploy script dùng ─────────────────────────────────────
mkdir -p /etc/sosflow

DB_PASSWORD_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$DB_PASSWORD', safe=''))")

cat > /etc/sosflow/env <<ENVFILE
DATABASE_URL=postgresql+psycopg2://sosflow:$DB_PASSWORD_ENCODED@$RDS_ENDPOINT/sosflow
CORS_ORIGINS=$CORS_ORIGINS
PRIORITY_RULES_PATH=/config/priority-rules.yaml
AI_PROVIDER=bedrock
AWS_REGION=$AWS_REGION
BEDROCK_INFERENCE_PROFILE_ARN=$BEDROCK_ARN
BEDROCK_MODEL_ID=$BEDROCK_MODEL
BEDROCK_TIMEOUT_SECONDS=$BEDROCK_TIMEOUT
BEDROCK_MAX_RETRIES=$BEDROCK_RETRIES
AI_FALLBACK_ENABLED=$AI_FALLBACK
DEMO_MODE=$DEMO_MODE
DEMO_TOKEN=$DEMO_TOKEN
SEED_ON_STARTUP=$SEED_ON_STARTUP
ENVFILE

chmod 600 /etc/sosflow/env

# Lưu image URL để redeploy script dùng
echo "$ECR_URL:latest" > /etc/sosflow/image_url

echo "=== SOSFlow startup complete! $(date) ==="
echo "Backend should be running on port 8000"
docker ps | grep sosflow-backend || echo "WARNING: container not running"
