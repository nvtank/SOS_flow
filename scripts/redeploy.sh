#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# SOSFlow Redeploy Script — dùng khi muốn update image mà không rebuild infra
# Chạy: bash scripts/redeploy.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

GREEN='\033[0;32m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${BLUE}[ℹ]${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$PROJECT_ROOT/infra"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
AWS_REGION="ap-southeast-1"
PROJECT_NAME="sosflow"
IMAGE_TAG="${IMAGE_TAG:-latest}"

cd "$INFRA_DIR"

# Lấy outputs từ Terraform state
ECR_URL=$(terraform output -raw ecr_backend_url)
ALB_URL=$(terraform output -raw alb_dns_name)
CF_URL=$(terraform output -raw cloudfront_url)
CF_DIST_ID=$(terraform output -raw cloudfront_distribution_id)
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
EC2_ID=$(terraform output -raw ec2_instance_id)

echo -e "${BOLD}${CYAN}══ Redeploying SOSFlow ══${NC}"
info "ECR: $ECR_URL"
info "EC2: $EC2_ID"

# ── Build & push new backend image ─────────────────────────────────────────────
cd "$PROJECT_ROOT"
info "Building new backend image..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_URL"

docker build -f backend/Dockerfile \
  -t "$ECR_URL:$IMAGE_TAG" \
  -t "$ECR_URL:latest" .

docker push "$ECR_URL:latest"
log "Backend image pushed"

# ── Restart container trên EC2 qua SSM ────────────────────────────────────────
info "Restarting backend container on EC2 via SSM..."
aws ssm send-command \
  --instance-ids "$EC2_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["/usr/local/bin/sosflow-redeploy.sh"]' \
  --region "$AWS_REGION" \
  --output text \
  --query 'Command.CommandId' > /tmp/ssm_cmd_id.txt

CMD_ID=$(cat /tmp/ssm_cmd_id.txt)
info "SSM Command ID: $CMD_ID — waiting for completion..."
sleep 15
aws ssm get-command-invocation \
  --command-id "$CMD_ID" \
  --instance-id "$EC2_ID" \
  --query 'StandardOutputContent' \
  --output text

log "Backend redeployed on EC2"

# ── Rebuild & re-upload frontend ──────────────────────────────────────────────
info "Rebuilding frontend..."
cd "$FRONTEND_DIR"
npm ci --silent
VITE_API_BASE_URL="$ALB_URL" \
VITE_DEMO_MODE="true" \
VITE_DEMO_TOKEN="sosflow-demo-2026" \
npm run build

aws s3 sync dist/ "s3://$FRONTEND_BUCKET/" --delete \
  --cache-control "public,max-age=31536000,immutable" \
  --exclude "index.html"

aws s3 cp dist/index.html "s3://$FRONTEND_BUCKET/index.html" \
  --cache-control "no-cache,no-store,must-revalidate" \
  --content-type "text/html"

aws cloudfront create-invalidation \
  --distribution-id "$CF_DIST_ID" \
  --paths "/*" > /dev/null

log "Frontend redeployed"

echo ""
echo -e "${BOLD}${GREEN}✅ Redeploy complete!${NC}"
echo -e "  🌐 Frontend  : ${CYAN}$CF_URL${NC}"
echo -e "  ⚙️  Backend   : ${CYAN}$ALB_URL${NC}"
