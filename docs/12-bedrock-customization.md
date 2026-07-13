# Bedrock customization readiness

## Baseline hiện tại

SOSFlow dùng baseline model qua Bedrock Converse API và ép output qua JSON Schema tại `ai/schemas/emergency-analysis.schema.json`. `AI_PROVIDER=mock` vẫn là mặc định để local/demo không phụ thuộc AWS. Khi có quyền IAM và model access, chọn baseline bằng `BEDROCK_MODEL_ID` hoặc `BEDROCK_INFERENCE_PROFILE_ARN`.

## Dataset và evaluation

Mỗi dòng JSONL là một mẫu tổng hợp/đã khử định danh: `message`, nhãn risk, nhãn missing information và giá trị extraction khi có. Giữ `training.example.jsonl`, `validation.example.jsonl` và `evaluation.jsonl` tách biệt. Trước mọi customization, chạy baseline:

```bash
python3 scripts/evaluate_analyzer.py --provider mock
python3 scripts/evaluate_analyzer.py --provider bedrock
```

So sánh JSON validity, extraction accuracy, precision/recall rủi ro và trường thiếu, latency, fallback rate cùng invocation count. Chỉ cân nhắc fine-tune khi lỗi trên tiếng Việt tự do lặp lại, có ảnh hưởng điều phối và dataset đã đủ lớn/được rà soát; không fine-tune chỉ để xử lý một vài prompt cá biệt.

## Sau khi job thật hoàn thành

Repository không tạo customization job và không phát sinh chi phí fine-tuning. Chỉ sau khi AWS báo job thành công, cấp custom model ARN và evaluation tốt hơn baseline mới cấu hình:

```dotenv
AI_PROVIDER=bedrock
BEDROCK_CUSTOM_MODEL_ARN=arn:aws:bedrock:...
```

Không ghi “trained model” trong README khi ARN đó chưa tồn tại. AWS credentials dùng default credential chain; không đưa access key vào `.env`.
