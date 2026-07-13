# SOSFlow AI Module — Huong dan chay & Deploy

## 1. Tong quan

Module `app/ai` la he thong AI phan tich bao cao khan cap va xep hang uu tien cuu ho cuu nan,
su dung **AWS Bedrock** (Converse API) ket hop voi **Nominatim** (OpenStreetMap) de geocode dia chi.

### Chuc nang chinh

| Chuc nang | Mo ta |
|-----------|-------|
| **Phan tich bao cao** | Trich xuat thong tin tu tin nhan khan cap: so nguoi, tre em, nguoi gia, bi thuong, mac ket, muc nuoc, nhu cau, vi tri... |
| **So sanh uu tien** | So sanh nhieu case va xep hang theo muc do uu tien cuu ho (CRITICAL / HIGH / MEDIUM / LOW) voi giai thich ly do |
| **Tinh khoang cach** | Tu dong geocode dia chi thanh toa do va tinh khoang cach toi tram cuu ho gan nhat (Haversine) |
| **Fallback** | Tu dong chuyen sang regex parser neu Bedrock loi |

---

## 2. Kien truc module

```
backend/app/ai/
├── __init__.py            # Package exports
├── .env                   # Cau hinh AWS Bedrock
├── schemas.py             # Pydantic models (AIAnalysis, PrioritizedCase, PriorityReport, ...)
├── bedrock.py             # Bedrock client — Converse API, retry, logging
├── analyzer.py            # HybridEmergencyAnalyzer (rule-based + LLM)
├── fallback.py            # Regex fallback khi Bedrock loi
├── prioritizer.py         # So sanh & xep hang uu tien + tinh khoang cach
├── geocoder.py            # Geocode dia chi -> toa do (Nominatim/OpenStreetMap)
├── evaluation.py          # Danh gia accuracy tren tap test
├── bedrock_cli.py         # CLI test interactive
├── prompts/
│   ├── emergency_system.txt   # System prompt cho phan tich bao cao
│   └── priority_system.txt    # System prompt cho xep hang uu tien
└── datasets/
    └── eval.json              # Tap test danh gia
```

### Luong xu ly (Pipeline)

```
Bao cao khan cap (text)
       │
       ▼
┌─────────────────┐
│  Bedrock / LLM  │──── loi ───▶ RegexFallbackAnalyzer
└────────┬────────┘
         │ AIAnalysis (JSON)
         ▼
┌─────────────────┐
│  Geocoder       │  Dia chi text → lat/lon (Nominatim API)
└────────┬────────┘
         │ lat, lon
         ▼
┌─────────────────┐
│  Prioritizer    │  Rule scoring + Distance bonus + LLM comparison
└────────┬────────┘
         │
         ▼
   PriorityReport (ranked cases + reasoning)
```

---

## 3. Dau vao & Dau ra

### 3.1. Phan tich bao cao

**Dau vao (Input):**

Mot chuoi text bao cao khan cap bang tieng Viet (co dau hoac khong dau).

```
Vi du:
  "Co 6 nguoi mac ket trong nha o xa Tan Binh, 2 tre em, 1 nguoi bi thuong,
   nuoc ngap 1.2 met, can thuoc va nuoc uong gap."
```

**Dau ra (Output): `AIAnalysis`**

```json
{
  "summary": "6 nguoi mac ket, 2 tre em, 1 bi thuong, ngap 1.2m",
  "normalized_message": "Co 6 nguoi mac ket trong nha...",
  "extracted_location": {
    "raw_text": "xa Tan Binh",
    "province": null,
    "district": null,
    "commune": "Tan Binh",
    "village": null,
    "latitude": 15.9721,
    "longitude": 108.0125
  },
  "number_of_people": 6,
  "number_of_children": 2,
  "number_of_elderly": null,
  "number_of_injured": 1,
  "is_trapped": true,
  "water_level": 1.2,
  "needs": ["medical", "water"],
  "detected_risks": ["trapped", "injury", "high_water"],
  "missing_information": [],
  "confidence": 0.92,
  "explanation": "Analyzed by Bedrock Converse API."
}
```

| Field | Type | Mo ta |
|-------|------|-------|
| `summary` | `str` | Tom tat tinh huong |
| `normalized_message` | `str` | Ban goc da lam sach |
| `extracted_location` | `ExtractedLocation` | Vi tri: raw text + tinh/huyen/xa/thon + lat/lon |
| `number_of_people` | `int \| null` | Tong so nguoi |
| `number_of_children` | `int \| null` | So tre em |
| `number_of_elderly` | `int \| null` | So nguoi gia |
| `number_of_injured` | `int \| null` | So nguoi bi thuong |
| `is_trapped` | `bool \| null` | Co bi mac ket khong |
| `water_level` | `float \| null` | Muc nuoc (met) |
| `needs` | `list[str]` | Nhu cau: medical, food, water, rescue, shelter, electricity |
| `detected_risks` | `list[str]` | Rui ro: trapped, injury, high_water |
| `missing_information` | `list[str]` | Thong tin con thieu |
| `confidence` | `float` | Do tin cay 0.0 - 1.0 |
| `explanation` | `str` | Giai thich nguon phan tich |

---

### 3.2. So sanh uu tien

**Dau vao (Input):**

Dict gom nhieu case, moi case la mot `AIAnalysis`:

```python
cases = {
    "case_001": analysis_1,   # AIAnalysis cua bao cao 1
    "case_002": analysis_2,   # AIAnalysis cua bao cao 2
    "case_003": analysis_3,   # AIAnalysis cua bao cao 3
}
```

**Dau ra (Output): `PriorityReport`**

```json
{
  "cases": [
    {
      "case_id": "case_003",
      "priority_score": 95.0,
      "priority_level": "CRITICAL",
      "reasoning": "10 nguoi mac ket, nuoc 2m, 3 bi thuong, 4 tre em ...",
      "nearest_station": "UBND Xa Tra Linh",
      "distance_km": 3.2,
      "original_analysis": { "..." }
    },
    {
      "case_id": "case_001",
      "priority_score": 53.0,
      "priority_level": "HIGH",
      "reasoning": "6 nguoi mac ket, 1 bi thuong, cach PCCC 40km ...",
      "nearest_station": "PCCC & CNCH Da Nang",
      "distance_km": 40.1,
      "original_analysis": { "..." }
    },
    {
      "case_id": "case_002",
      "priority_score": 12.0,
      "priority_level": "LOW",
      "reasoning": "3 nguoi, nuoc 0.5m, gan benh vien ...",
      "nearest_station": "Benh vien Da Nang",
      "distance_km": 1.5,
      "original_analysis": { "..." }
    }
  ],
  "overall_summary": "Case_003 khan cap nhat, can cuu ho ngay. Case_001 tiep theo..."
}
```

| Field | Type | Mo ta |
|-------|------|-------|
| `cases` | `list[PrioritizedCase]` | Danh sach case da sap xep (uu tien giam dan) |
| `cases[].case_id` | `str` | ID cua case |
| `cases[].priority_score` | `float` | Diem uu tien 0-100 |
| `cases[].priority_level` | `str` | CRITICAL / HIGH / MEDIUM / LOW |
| `cases[].reasoning` | `str` | Giai thich ly do xep hang |
| `cases[].nearest_station` | `str \| null` | Tram cuu ho gan nhat |
| `cases[].distance_km` | `float \| null` | Khoang cach toi tram (km) |
| `overall_summary` | `str` | Tong ket va khuyen nghi thu tu cuu ho |

### Cach tinh diem uu tien

**Tang 1 — Rule-based scoring (0-100 diem):**

| Yeu to | Diem |
|--------|------|
| Mac ket (is_trapped) | +30 |
| Bi thuong | +5 moi nguoi (max +25) |
| Tre em | +4 moi tre (max +16) |
| Nguoi gia | +4 moi nguoi (max +16) |
| Muc nuoc | +3 moi 0.5m (max +18) |
| So nguoi | +1 moi nguoi (max +10) |
| Rui ro | +3 moi risk (max +15) |
| Nhu cau | +2 moi need (max +10) |

**Tang 2 — Distance tiebreaker (0-8 diem bonus):**

Khi hai case co diem tuong duong, case xa tram cuu ho hon duoc cong them diem
(vi cuu ho mat nhieu thoi gian hon de tiep can):

| Khoang cach | Bonus |
|-------------|-------|
| 0 km | +0 |
| 5 km | +2 |
| 20 km | +4 |
| 50 km | +6 |
| 100+ km | +8 |

Cong thuc: `bonus = 2 * ln(1 + distance/5)`, gioi han 8 diem.

**Tang 3 — LLM comparison (tuy chon):**

Neu mode=bedrock, gui tat ca case len Bedrock de LLM so sanh nguc anh,
giai thich ly do uu tien bang ngon ngu tu nhien.

---

### 3.3. Geocoding

**Dau vao:** Dia chi text (VD: `"40 Trung Nu Vuong, Son Tra, Da Nang"`)

**Dau ra:** `(latitude, longitude, display_name)` hoac `None`

Su dung Nominatim (OpenStreetMap API), mien phi, rate limit 1 req/giay.

### 3.4. Tram cuu ho co dinh (demo)

| Tram | Toa do | Loai |
|------|--------|------|
| UBND Xa Tra Linh | 15.023565, 108.041263 | admin |
| PCCC & CNCH Da Nang | 16.035971, 108.213402 | rescue |
| Benh vien Da Nang | 16.072259, 108.216008 | medical |

---

## 4. Yeu cau he thong

### Python
- Python 3.11+

### Thu vien Python
```bash
pip install boto3 python-dotenv pydantic httpx
```

> `httpx` da co trong `requirements.txt`, dung cho geocoder.
> `boto3` can cai them de goi AWS Bedrock.

### AWS Credentials

Can co AWS credentials voi quyen truy cap **Amazon Bedrock Runtime**.

**Cach 1 — File credentials (khuyen nghi cho dev):**
```
# ~/.aws/credentials
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

**Cach 2 — Bien moi truong:**
```bash
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
export AWS_REGION=ap-southeast-1
```

**Cach 3 — IAM Role (cho EC2/ECS/Lambda — khuyen nghi cho production):**

Gan IAM Role voi policy `AmazonBedrockFullAccess`.

### IAM Policy toi thieu

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["bedrock:InvokeModel", "bedrock:Converse"],
            "Resource": "*"
        }
    ]
}
```

---

## 5. Cau hinh

### File `.env` (`backend/app/ai/.env`)

```env
# AWS Bedrock
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
BEDROCK_INFERENCE_PROFILE_ID=arn:aws:bedrock:ap-southeast-1:YOUR_ACCOUNT_ID:inference-profile/apac.amazon.nova-lite-v1:0
AWS_REGION=ap-southeast-1
BEDROCK_MAX_TOKENS=2048

# AI mode: mock | hybrid | bedrock
SOSFLOW_AI_MODE=bedrock
```

| Bien | Mo ta | Mac dinh |
|------|-------|----------|
| `BEDROCK_MODEL_ID` | ID model Bedrock | `amazon.nova-lite-v1:0` |
| `BEDROCK_INFERENCE_PROFILE_ID` | ARN inference profile (cross-region) | _(trong)_ |
| `AWS_REGION` | AWS Region | `ap-southeast-1` |
| `BEDROCK_MAX_TOKENS` | So token toi da cho response | `2048` |
| `SOSFLOW_AI_MODE` | Che do AI | `bedrock` |

### Cac model ho tro

| Model | ID | Chi phi | Ghi chu |
|-------|----|---------|---------|
| Amazon Nova Lite | `amazon.nova-lite-v1:0` | Re nhat | Nhanh, phu hop dev/test |
| Amazon Nova Pro | `amazon.nova-pro-v1:0` | Trung binh | Can bang chat luong/toc do |
| Claude 3 Haiku | `anthropic.claude-3-haiku-*` | Re | Chat luong cao, tieng Viet tot |
| Claude 3.5 Sonnet | `anthropic.claude-3-5-sonnet-*` | Cao | Chat luong cao nhat |

---

## 6. Chay test (CLI)

### Khoi dong
```bash
cd backend
python -m app.ai.bedrock_cli                  # mac dinh mode=bedrock
python -m app.ai.bedrock_cli --mode hybrid    # hybrid (rule + LLM)
python -m app.ai.bedrock_cli --mode mock      # mock (chi rule-based, khong can AWS)
```

### Cac lenh trong CLI

| Lenh | Mo ta |
|------|-------|
| _(nhap text)_ | Phan tich 1 bao cao khan cap |
| `compare` | Vao che do so sanh nhieu case |
| `stations` | Hien thi danh sach tram cuu ho |
| `mode` | Xem mode hien tai |
| `help` | Hien thi huong dan |
| `quit` | Thoat |

### Vi du: So sanh uu tien voi dia chi tu dong geocode

```
> Nhap bao cao: compare

  Case #1: 5 nguoi mac ket, 2 tre em o 40 Trung Nu Vuong, Son Tra, Da Nang
  Case #2: 3 nguoi, 1 bi thuong, ngap 0.5m o Thon 3, Xa Tra Linh, Da Nang
  Case #3: done

  BAO CAO UU TIEN CUU HO  (3.5s)

  #1  [HIGH]  Case_1  (score: 53 | 1.9km -> Benh vien Da Nang)
      Toa do  : 16.0712, 108.2155   ← tu dong geocode tu dia chi
      Facts   : 5 nguoi, 2 tre em, MAC KET

  #2  [LOW]   Case_2  (score: 15 | 0.4km -> UBND Xa Tra Linh)
      Toa do  : 15.0230, 108.0410   ← tu dong geocode tu dia chi
      Facts   : 3 nguoi, 1 bi thuong, nuoc 0.5m
```

### Cach nhap toa do thu cong

Neu khong muon dung geocoder, them `@lat,lon` cuoi bao cao:

```
Case #1: 5 nguoi mac ket @16.071,108.215
```

---

## 7. Tich hop vao FastAPI

### Code mau

```python
from app.ai import AIAnalyzerFactory, EmergencyPrioritizer

analyzer = AIAnalyzerFactory.create("bedrock")
prioritizer = EmergencyPrioritizer(mode="bedrock")


# --- Phan tich 1 bao cao ---
@router.post("/analyze")
async def analyze_report(message: str):
    result = await analyzer.analyze(message)
    return result.model_dump()


# --- So sanh uu tien nhieu case ---
@router.post("/prioritize")
async def prioritize_cases(messages: list[str]):
    cases = {}
    for i, msg in enumerate(messages, 1):
        analysis = await analyzer.analyze(msg)
        cases[f"case_{i:03d}"] = analysis

    report = await prioritizer.prioritize(cases)
    return report.model_dump()
```

---

## 8. Deploy

### 8.1. Local (Development)

```bash
cd backend
pip install -r requirements.txt
pip install boto3
# Cau hinh ~/.aws/credentials + .env
uvicorn app.main:app --reload --port 8000
```

### 8.2. Docker

Them `boto3` vao `requirements.txt`, truyen AWS credentials qua env:

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_REGION: ap-southeast-1
      BEDROCK_MODEL_ID: amazon.nova-lite-v1:0
      SOSFLOW_AI_MODE: bedrock
```

```bash
docker-compose up --build
```

### 8.3. AWS EC2

```bash
# 1. Launch EC2 + gan IAM Role voi AmazonBedrockFullAccess
# 2. Khong can set AWS credentials — IAM Role tu cung cap
export AWS_REGION=ap-southeast-1
docker-compose up -d --build
```

### 8.4. AWS ECS (Production khuyen nghi)

```
1. Push image len ECR
2. Tao Task Definition voi Task Role co AmazonBedrockFullAccess
3. Tao ECS Service (Fargate) + ALB
4. Environment variables: AWS_REGION, BEDROCK_MODEL_ID, SOSFLOW_AI_MODE
```

### 8.5. AWS Lambda (Serverless)

```
1. Dung Mangum lam ASGI adapter: pip install mangum
2. Handler: from mangum import Mangum; handler = Mangum(app)
3. Deploy qua SAM/CDK, gan IAM Role
```

---

## 9. Troubleshooting

| Loi | Nguyen nhan | Cach sua |
|-----|-------------|----------|
| `RuntimeError: boto3 is required` | Chua cai boto3 | `pip install boto3` |
| `AccessDeniedException` | IAM khong co quyen Bedrock | Them policy `AmazonBedrockFullAccess` |
| `ResourceNotFoundException` | Model chua kich hoat | AWS Console > Bedrock > Model access |
| `ThrottlingException` | Vuot rate limit | He thong tu retry 3 lan |
| Geocode tra `None` | Dia chi khong tim thay tren OpenStreetMap | Dung `@lat,lon` thu cong |
| Fallback regex | Bedrock loi nen dung regex | Kiem tra AWS credentials |

### Kiem tra nhanh

```bash
# Test ket noi AWS
aws sts get-caller-identity

# Test AI module (khong can Bedrock)
cd backend
python -m app.ai.bedrock_cli --mode mock

# Test geocoder
python -c "import asyncio; from app.ai.geocoder import geocode_address; print(asyncio.run(geocode_address('40 Trung Nu Vuong, Da Nang')))"
```
