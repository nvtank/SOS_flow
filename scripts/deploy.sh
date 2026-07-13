#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# SOSFlow Full Deploy Script
# Chạy từ WSL: bash scripts/deploy.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Colors ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()     { echo -e "${GREEN}[✓]${NC} $*"; }
info()    { echo -e "${BLUE}[ℹ]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }
step()    { echo -e "\n${BOLD}${CYAN}══ $* ══${NC}"; }

# ── Config ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$PROJECT_ROOT/infra"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
AWS_REGION="ap-southeast-1"
PROJECT_NAME="sosflow"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# ── Step 0: Kiểm tra prerequisites ────────────────────────────────────────────
step "0/6 Checking prerequisites"

for cmd in terraform aws docker; do
  if command -v "$cmd" &>/dev/null; then
    log "$cmd found: $(${cmd} --version 2>&1 | head -1)"
  else
    error "$cmd not found! Install it first."
  fi
done

# Kiểm tra AWS credentials
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>&1) || error "AWS credentials not configured! Run: aws configure"
log "AWS Account: $ACCOUNT_ID | Region: $AWS_REGION"

if [ "$ACCOUNT_ID" != "197826770971" ]; then
  warn "Account ID $ACCOUNT_ID khác với expected 197826770971 — tiếp tục anyway"
fi

# Kiểm tra Docker daemon
docker info &>/dev/null || error "Docker daemon not running!"

# ── Step 1: Terraform init + Phase 1 (chỉ ECR) ────────────────────────────────
step "1/6 Terraform init & create ECR"

cd "$INFRA_DIR"
terraform init -upgrade

# Tạo ECR repo trước để có chỗ push image
info "Creating ECR repository..."
terraform apply \
  -target=aws_ecr_repository.backend \
  -target=aws_ecr_lifecycle_policy.backend \
  -auto-approve

ECR_URL=$(terraform output -raw ecr_backend_url)
log "ECR URL: $ECR_URL"

# ── Step 2: Build & Push Docker image ─────────────────────────────────────────
step "2/6 Build & push backend image to ECR"

cd "$PROJECT_ROOT"

# Login ECR
info "Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_URL"

# Build backend image
info "Building backend Docker image..."
docker build \
  -f backend/Dockerfile \
  -t "$PROJECT_NAME-backend:$IMAGE_TAG" \
  -t "$ECR_URL:$IMAGE_TAG" \
  -t "$ECR_URL:latest" \
  .

log "Backend image built successfully"

# Push to ECR
info "Pushing to ECR..."
docker push "$ECR_URL:$IMAGE_TAG"
docker push "$ECR_URL:latest"
log "Backend image pushed: $ECR_URL:latest"

# ── Step 3: Terraform apply toàn bộ infra ─────────────────────────────────────
step "3/6 Terraform apply full infrastructure"

cd "$INFRA_DIR"
info "This will create: VPC, EC2, RDS, Redis, ALB, S3, CloudFront..."
info "Estimated time: 10-15 minutes"

terraform apply -auto-approve

# Lấy outputs
ALB_URL=$(terraform output -raw alb_dns_name)
CF_URL=$(terraform output -raw cloudfront_url)
CF_DIST_ID=$(terraform output -raw cloudfront_distribution_id)
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
EC2_ID=$(terraform output -raw ec2_instance_id)

log "ALB URL: $ALB_URL"
log "CloudFront URL: $CF_URL"
log "EC2 Instance ID: $EC2_ID"
log "Frontend Bucket: $FRONTEND_BUCKET"

# ── Cập nhật CORS trên EC2 với CloudFront URL thực ────────────────────────────
info "Waiting 60s for EC2 to boot before updating CORS..."
sleep 60

info "Updating CORS_ORIGINS on EC2 to include CloudFront URL..."
aws ssm send-command \
  --instance-ids "$EC2_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[
    \"sed -i 's|CORS_ORIGINS=.*|CORS_ORIGINS=$CF_URL,http://$ALB_URL|' /etc/sosflow/env\",
    \"docker stop sosflow-backend || true\",
    \"docker rm sosflow-backend || true\",
    \"docker run -d --name sosflow-backend --restart unless-stopped -p 8000:8000 --env-file /etc/sosflow/env \$(cat /etc/sosflow/image_url)\",
    \"echo CORS updated: $CF_URL\"
  ]" \
  --region "$AWS_REGION" \
  --output text \
  --query 'Command.CommandId' > /dev/null 2>&1 || warn "SSM CORS update failed — EC2 chưa sẵn sàng, thử lại bằng scripts/redeploy.sh"

log "CORS update triggered"

# ── Step 4: Build Frontend ─────────────────────────────────────────────────────
step "4/6 Build frontend (VITE_API_BASE_URL → ALB)"

cd "$FRONTEND_DIR"

# Cài node packages
info "Installing npm packages..."
npm ci --silent

# Build với ALB URL
info "Building React app với VITE_API_BASE_URL=$ALB_URL..."
VITE_API_BASE_URL="$ALB_URL" \
VITE_DEMO_MODE="true" \
VITE_DEMO_TOKEN="sosflow-demo-2026" \
npm run build

log "Frontend built successfully → dist/"

# ── Step 5: Upload Frontend lên S3 ────────────────────────────────────────────
step "5/6 Upload frontend to S3 & invalidate CloudFront"

info "Syncing dist/ → s3://$FRONTEND_BUCKET..."
aws s3 sync dist/ "s3://$FRONTEND_BUCKET/" \
  --delete \
  --cache-control "public,max-age=31536000,immutable" \
  --exclude "index.html"

# index.html: không cache để luôn lấy version mới
aws s3 cp dist/index.html "s3://$FRONTEND_BUCKET/index.html" \
  --cache-control "no-cache,no-store,must-revalidate" \
  --content-type "text/html"

log "Frontend uploaded to S3"

# Invalidate CloudFront cache
info "Invalidating CloudFront distribution $CF_DIST_ID..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$CF_DIST_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)
log "CloudFront invalidation created: $INVALIDATION_ID"

# ── Step 6: Health check & summary ────────────────────────────────────────────
step "6/6 Health check"

info "Waiting 30s for EC2 to initialize..."
sleep 30

# Test backend health (qua ALB)
info "Testing backend health endpoint..."
for i in 1 2 3 4 5 6 7 8 9 10; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$ALB_URL/health" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    log "Backend health check PASSED (HTTP 200)"
    break
  fi
  if [ "$i" = "10" ]; then
    warn "Backend health check failed after 10 tries (HTTP $STATUS)"
    warn "EC2 đang khởi động — check lại sau 5 phút: curl $ALB_URL/health"
    warn "Xem logs: aws ssm start-session --target $EC2_ID"
  fi
  info "Attempt $i: HTTP $STATUS — retrying in 30s..."
  sleep 30
done

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════"
echo "  🎉 SOSFlow deployed successfully!"
echo "════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  🌐 ${BOLD}Frontend${NC}  : ${CYAN}$CF_URL${NC}"
echo -e "  ⚙️  ${BOLD}Backend${NC}   : ${CYAN}$ALB_URL${NC}"
echo -e "  📋 ${BOLD}API Docs${NC}  : ${CYAN}$ALB_URL/docs${NC}"
echo -e "  🗺️  ${BOLD}Reporter${NC}  : ${CYAN}$CF_URL/report${NC}"
echo -e "  📊 ${BOLD}Dashboard${NC} : ${CYAN}$CF_URL/admin/dashboard${NC}"
echo ""
echo -e "  🖥️  ${BOLD}EC2 SSH${NC} (SSM): aws ssm start-session --target $EC2_ID"
echo -e "  🔄 ${BOLD}Redeploy${NC}: bash scripts/redeploy.sh"
echo ""
echo -e "  Demo token: ${YELLOW}sosflow-demo-2026${NC}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════${NC}"
