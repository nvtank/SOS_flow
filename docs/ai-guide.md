# SOSFlow AI Module — Hướng dẫn chạy & Deploy

## Tổng quan

Module `app/ai` là hệ thống AI phân tích báo cáo khẩn cấp và xếp hạng ưu tiên cứu hộ, sử dụng **AWS Bedrock** (Converse API).

### Chức năng chính

| Chức năng | Mô tả |
|-----------|-------|
| **Phân tích báo cáo** | Trích xuất thông tin từ tin nhắn khẩn cấp (số người, trẻ em, người già, bị thương, mắc kẹt, mực nước, nhu cầu...) |
| **So sánh ưu tiên** | So sánh nhiều case và xếp hạng theo mức độ ưu tiên cứu hộ (CRITICAL / HIGH / MEDIUM / LOW) với giải thích lý do |
| **Fallback** | Tự động chuyển sang regex parser nếu Bedrock lỗi |

### Kiến trúc module

```
backend/app/ai/
├── __init__.py          # Package exports
├── .env                 # Cấu hình AWS Bedrock (không commit lên git)
├── schemas.py           # Pydantic models (AIAnalysis, PrioritizedCase, PriorityReport)
├── bedrock.py           # Bedrock client — Converse API, retry, logging
├── analyzer.py          # HybridEmergencyAnalyzer (rule-based + LLM)
├── fallback.py          # Regex fallback khi Bedrock lỗi
├── prioritizer.py       # So sánh & xếp hạng ưu tiên cứu hộ
├── evaluation.py        # Đánh giá accuracy trên tập test
├── bedrock_cli.py       # CLI test interactive
├── prompts/
│   ├── emergency_system.txt   # System prompt cho phân tích báo cáo
│   └── priority_system.txt    # System prompt cho xếp hạng ưu tiên
└── datasets/
    └── eval.json              # Tập test đánh giá
```

---

## 1. Yêu cầu hệ thống

### Python
- Python 3.11+

### Thư viện Python
```bash
pip install boto3 python-dotenv pydantic
```

> **Lưu ý**: `boto3` là bắt buộc để gọi AWS Bedrock. Các thư viện còn lại (`fastapi`, `uvicorn`, ...) đã có trong `requirements.txt` của backend.

### AWS Credentials

Cần có AWS credentials với quyền truy cập **Amazon Bedrock Runtime**. Có 3 cách cấu hình:

#### Cách 1: AWS credentials file (khuyến nghị cho dev)
```
# File: ~/.aws/credentials
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

#### Cách 2: Biến môi trường
```bash
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
export AWS_REGION=ap-southeast-1
```

#### Cách 3: IAM Role (cho EC2/ECS/Lambda — khuyến nghị cho production)
Gắn IAM Role với policy `AmazonBedrockFullAccess` vào instance/task/function.

### IAM Policy tối thiểu

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:Converse"
            ],
            "Resource": "*"
        }
    ]
}
```

### Kích hoạt model trên Bedrock Console

Trước khi dùng, cần vào **AWS Console > Amazon Bedrock > Model access** và bật model mà bạn muốn sử dụng (ví dụ: Amazon Nova Lite, Claude 3 Haiku, ...).

---

## 2. Cấu hình

### File `.env` (backend/app/ai/.env)

```env
# AWS Bedrock configuration
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0

# Nếu dùng inference profile (cross-region), set ARN ở đây
BEDROCK_INFERENCE_PROFILE_ID=arn:aws:bedrock:ap-southeast-1:YOUR_ACCOUNT_ID:inference-profile/apac.amazon.nova-lite-v1:0

# Region
AWS_REGION=ap-southeast-1

# Max tokens cho response
BEDROCK_MAX_TOKENS=2048

# AI mode: mock | hybrid | bedrock
SOSFLOW_AI_MODE=bedrock
```

### Giải thích các biến

| Biến | Mô tả | Giá trị mặc định |
|------|--------|-------------------|
| `BEDROCK_MODEL_ID` | ID model Bedrock | `amazon.nova-lite-v1:0` |
| `BEDROCK_INFERENCE_PROFILE_ID` | ARN của inference profile (nếu dùng cross-region) | _(trống)_ |
| `AWS_REGION` | AWS Region | `ap-southeast-1` |
| `BEDROCK_MAX_TOKENS` | Số token tối đa cho response | `2048` |
| `SOSFLOW_AI_MODE` | Chế độ AI | `bedrock` |

### Các model hỗ trợ

| Model | Model ID | Chi phí | Ghi chú |
|-------|----------|---------|---------|
| Amazon Nova Lite | `amazon.nova-lite-v1:0` | Rẻ nhất | Tốc độ nhanh, phù hợp cho dev/test |
| Amazon Nova Pro | `amazon.nova-pro-v1:0` | Trung bình | Cân bằng chất lượng/tốc độ |
| Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0` | Rẻ | Chất lượng cao, tiếng Việt tốt |
| Claude 3.5 Sonnet | `anthropic.claude-3-5-sonnet-20240620-v1:0` | Cao | Chất lượng cao nhất |

---

## 3. Chạy test nhanh (CLI)

### Khởi động CLI interactive
```bash
cd backend
python -m app.ai.bedrock_cli
```

### Chọn mode
```bash
# Bedrock thật (mặc định)
python -m app.ai.bedrock_cli --mode bedrock

# Hybrid: rule-based + LLM
python -m app.ai.bedrock_cli --mode hybrid

# Mock: chỉ rule-based, không cần AWS
python -m app.ai.bedrock_cli --mode mock
```

### Các lệnh trong CLI

| Lệnh | Mô tả |
|-------|--------|
| _(nhập text)_ | Phân tích 1 báo cáo khẩn cấp |
| `compare` | Vào chế độ so sánh nhiều case |
| `mode` | Xem mode hiện tại |
| `help` | Hiện hướng dẫn |
| `quit` / `exit` | Thoát |

### Ví dụ: Phân tích 1 báo cáo

```
> Nhap bao cao: Co 6 nguoi mac ket trong nha, 2 tre em, 1 nguoi bi thuong

-------------------------------------------------------
  Ket qua phan tich  (1.34s)
-------------------------------------------------------
         Summary  6 people trapped in a house, 2 children, 1 injured
        Location  N/A
          People  6
        Children  2
         Injured  1
         Trapped  True
           Needs  medicine, water
      Confidence  0.90
-------------------------------------------------------
```

### Ví dụ: So sánh ưu tiên nhiều case

```
> Nhap bao cao: compare

  CHE DO SO SANH UU TIEN
  Nhap tung bao cao, moi bao cao 1 dong.
  Go 'done' khi da nhap het de bat dau so sanh.

  Case #1: 10 nguoi mac ket tren noc nha, ngap 2 met, 3 nguoi bi thuong nang, 4 tre em
  Case #2: Co 6 nguoi mac ket, 2 tre em, 1 bi thuong, can thuoc
  Case #3: Nha bi ngap 0.5 met, 3 nguoi, can luong thuc
  Case #4: done

============================================================
  BAO CAO UU TIEN CUU HO  (2.34s)
============================================================

  #1  [CRITICAL]  Case_1  (score: 99)
      Ly do: 10 nguoi mac ket, nuoc 2m, 3 bi thuong, 4 tre em — life-threatening

  #2  [HIGH]      Case_2  (score: 53)
      Ly do: 6 nguoi trapped, 1 injured, 2 tre em, can medicine

  #3  [LOW]       Case_3  (score: 8)
      Ly do: 3 nguoi, nuoc 0.5m, khong co rui ro khan cap
============================================================
```

---

## 4. Chạy evaluation

Đánh giá accuracy trên tập test `datasets/eval.json`:

```bash
cd backend

# Mock mode
python -m app.ai.evaluation mock --verbose

# Bedrock mode
python -m app.ai.evaluation bedrock --verbose
```

---

## 5. Tích hợp vào FastAPI backend

### Sử dụng trong API endpoint

```python
from app.ai import AIAnalyzerFactory, EmergencyPrioritizer, AIAnalysis

# --- Phân tích 1 báo cáo ---
analyzer = AIAnalyzerFactory.create("bedrock")  # hoặc "mock", "hybrid"
result: AIAnalysis = await analyzer.analyze("Co 6 nguoi mac ket...")

# --- So sánh ưu tiên ---
prioritizer = EmergencyPrioritizer(mode="bedrock")  # hoặc "rule"
report = await prioritizer.prioritize({
    "case_001": analysis_1,
    "case_002": analysis_2,
    "case_003": analysis_3,
})
# report.cases → danh sách đã sắp xếp theo ưu tiên
# report.overall_summary → tóm tắt tổng thể
```

### Ví dụ FastAPI endpoint

```python
from fastapi import APIRouter, HTTPException
from app.ai import AIAnalyzerFactory, EmergencyPrioritizer

router = APIRouter(prefix="/api/ai", tags=["AI"])

analyzer = AIAnalyzerFactory.create("bedrock")
prioritizer = EmergencyPrioritizer(mode="bedrock")


@router.post("/analyze")
async def analyze_report(message: str):
    """Phân tích 1 báo cáo khẩn cấp."""
    result = await analyzer.analyze(message)
    return result.model_dump()


@router.post("/prioritize")
async def prioritize_cases(messages: list[str]):
    """So sánh và xếp hạng nhiều case."""
    # Phân tích từng case
    cases = {}
    for i, msg in enumerate(messages, start=1):
        analysis = await analyzer.analyze(msg)
        cases[f"case_{i:03d}"] = analysis

    # Xếp hạng
    report = await prioritizer.prioritize(cases)
    return report.model_dump()
```

---

## 6. Deploy

### 6.1. Deploy local (Development)

```bash
# 1. Cài dependencies
cd backend
pip install -r requirements.txt
pip install boto3

# 2. Cấu hình AWS credentials
# Tạo file ~/.aws/credentials hoặc set biến môi trường

# 3. Cấu hình .env
# Sửa file backend/app/ai/.env theo mục 2

# 4. Chạy FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 6.2. Deploy Docker

#### Cập nhật requirements.txt

Thêm `boto3` vào `backend/requirements.txt`:
```
boto3>=1.35.0
```

#### Cập nhật docker-compose.yml

Thêm biến môi trường AWS vào service `backend`:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    environment:
      DATABASE_URL: postgresql+psycopg2://sosflow:sosflow@postgres:5432/sosflow
      CORS_ORIGINS: http://localhost:5173

      # --- AI Configuration ---
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_REGION: ap-southeast-1
      BEDROCK_MODEL_ID: amazon.nova-lite-v1:0
      BEDROCK_INFERENCE_PROFILE_ID: ${BEDROCK_INFERENCE_PROFILE_ID}
      BEDROCK_MAX_TOKENS: "2048"
      SOSFLOW_AI_MODE: bedrock
    ports:
      - "8000:8000"
```

#### Chạy Docker

```bash
# Set credentials qua biến môi trường
export AWS_ACCESS_KEY_ID=YOUR_KEY
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET

# Hoặc tạo file .env ở root project
echo "AWS_ACCESS_KEY_ID=YOUR_KEY" >> .env
echo "AWS_SECRET_ACCESS_KEY=YOUR_SECRET" >> .env

# Build & run
docker-compose up --build
```

### 6.3. Deploy AWS EC2

```bash
# 1. Launch EC2 instance (Amazon Linux 2023 / Ubuntu 22.04+)
# 2. Gắn IAM Role với policy AmazonBedrockFullAccess
# 3. SSH vào instance

# Cài Docker
sudo yum install -y docker        # Amazon Linux
sudo apt install -y docker.io     # Ubuntu
sudo systemctl start docker

# Clone repo
git clone <repo-url> && cd SOS_flow

# Không cần set AWS credentials — IAM Role tự cung cấp
# Chỉ cần set region
export AWS_REGION=ap-southeast-1

# Build & run
docker-compose up -d --build
```

### 6.4. Deploy AWS ECS (Production)

Đây là cách deploy production khuyến nghị:

```
1. Push Docker image lên ECR
   - aws ecr create-repository --repository-name sosflow-backend
   - docker build -t sosflow-backend -f backend/Dockerfile .
   - docker tag sosflow-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/sosflow-backend:latest
   - docker push <account>.dkr.ecr.<region>.amazonaws.com/sosflow-backend:latest

2. Tạo ECS Task Definition
   - Container image: ECR image ở trên
   - Task Role: IAM Role với AmazonBedrockFullAccess
   - Environment variables:
     - AWS_REGION=ap-southeast-1
     - BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
     - SOSFLOW_AI_MODE=bedrock
     - DATABASE_URL=<RDS connection string>

3. Tạo ECS Service
   - Launch type: Fargate
   - Network: VPC với public subnet + ALB
   - Auto-scaling: min=1, max=4

4. Tạo ALB (Application Load Balancer)
   - Target group: ECS service port 8000
   - Health check: GET /docs
```

### 6.5. Deploy AWS Lambda (Serverless)

Phù hợp nếu traffic thấp và muốn tiết kiệm chi phí:

```
1. Đóng gói bằng Mangum (ASGI adapter cho Lambda)
   pip install mangum

2. Handler:
   from mangum import Mangum
   from app.main import app
   handler = Mangum(app)

3. Deploy qua SAM hoặc CDK
4. Gắn IAM Role với policy AmazonBedrockFullAccess
5. Set environment variables trong Lambda configuration
```

---

## 7. Monitoring & Logging

### Log levels

Module sử dụng `logging` chuẩn Python. Các log quan trọng:

| Logger | Level | Nội dung |
|--------|-------|----------|
| `app.ai.bedrock` | INFO | Thời gian gọi Bedrock, response size |
| `app.ai.bedrock` | WARNING | Retry khi bị throttle |
| `app.ai.bedrock` | ERROR | Bedrock lỗi, chuyển sang fallback |
| `app.ai.prioritizer` | INFO | Thời gian so sánh ưu tiên |

### Bật debug log

```python
import logging
logging.getLogger("app.ai").setLevel(logging.DEBUG)
```

### CloudWatch (nếu deploy trên AWS)

Log tự động xuất ra stdout → CloudWatch Logs (khi chạy trên ECS/Lambda).

---

## 8. Troubleshooting

### Lỗi thường gặp

| Lỗi | Nguyên nhân | Cách sửa |
|------|-------------|----------|
| `RuntimeError: boto3 is required` | Chưa cài boto3 | `pip install boto3` |
| `RuntimeError: Cần set BEDROCK_MODEL_ID...` | Chưa cấu hình .env | Tạo file `.env` theo mục 2 |
| `AccessDeniedException` | IAM không có quyền Bedrock | Thêm policy `AmazonBedrockFullAccess` |
| `ResourceNotFoundException` | Model chưa được kích hoạt | Vào AWS Console > Bedrock > Model access |
| `ThrottlingException` | Vượt quá rate limit | Hệ thống tự retry 3 lần. Nếu vẫn lỗi, tăng quota |
| `ValidationException` | Model không hỗ trợ Converse API | Đổi sang model khác (Nova, Claude) |
| Fallback regex | Bedrock lỗi nên dùng regex | Kiểm tra AWS credentials và model access |

### Kiểm tra nhanh

```bash
# Test kết nối AWS
aws sts get-caller-identity

# Test Bedrock model access
aws bedrock list-foundation-models --region ap-southeast-1 --query "modelSummaries[?modelId=='amazon.nova-lite-v1:0']"

# Test AI module (không cần Bedrock)
cd backend
python -m app.ai.bedrock_cli --mode mock
```
