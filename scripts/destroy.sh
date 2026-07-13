#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# SOSFlow Destroy Script — Teardown toàn bộ AWS resources
# Chạy: bash scripts/destroy.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'; BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")/infra"
AWS_REGION="ap-southeast-1"
PROJECT_NAME="sosflow"

echo -e "${RED}${BOLD}⚠️  WARNING: Đây sẽ XÓA TOÀN BỘ AWS resources của SOSFlow!${NC}"
echo -e "  - EC2, RDS, Redis, ALB, VPC"
echo -e "  - S3 buckets (frontend + logs)"
echo -e "  - CloudFront, ECR, Secrets Manager"
echo -e "  - ${YELLOW}DỮ LIỆU SẼ KHÔNG PHỤC HỒI ĐƯỢC!${NC}"
echo ""
read -rp "Gõ 'yes' để xác nhận destroy: " confirm

if [ "$confirm" != "yes" ]; then
  echo "Huỷ. Không có gì bị xóa."
  exit 0
fi

# ── Xóa ECR images trước (force_destroy không xóa images) ─────────────────────
echo -e "\n${YELLOW}[1/3]${NC} Deleting ECR images..."
ECR_REPO="$PROJECT_NAME-backend"
IMAGES=$(aws ecr list-images \
  --repository-name "$ECR_REPO" \
  --region "$AWS_REGION" \
  --query 'imageIds[*]' \
  --output json 2>/dev/null || echo "[]")

if [ "$IMAGES" != "[]" ] && [ "$IMAGES" != "null" ]; then
  aws ecr batch-delete-image \
    --repository-name "$ECR_REPO" \
    --region "$AWS_REGION" \
    --image-ids "$IMAGES" || true
  echo -e "${GREEN}ECR images deleted${NC}"
fi

# ── Terraform destroy ──────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[2/3]${NC} Running terraform destroy..."
cd "$INFRA_DIR"
terraform destroy -auto-approve

# ── Xóa local state (optional) ────────────────────────────────────────────────
echo -e "\n${YELLOW}[3/3]${NC} Cleaning up local terraform state..."
read -rp "Xóa terraform.tfstate local? (y/N): " del_state
if [ "$del_state" = "y" ]; then
  rm -f terraform.tfstate terraform.tfstate.backup .terraform.lock.hcl
  rm -rf .terraform/
  echo -e "${GREEN}Local state deleted${NC}"
fi

echo ""
echo -e "${GREEN}${BOLD}✅ Destroy complete. Tất cả AWS resources đã được xóa.${NC}"
