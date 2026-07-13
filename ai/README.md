# SOSFlow AI datasets

Các dataset này dùng dữ liệu tổng hợp, không có thông tin cá nhân thật. `evaluation.jsonl` là baseline 40 tin tiếng Việt cho mock/Bedrock; các file training/validation chỉ là ví dụ format, không phải dữ liệu đã dùng để fine-tune. Chạy `python3 scripts/evaluate_analyzer.py --provider mock` để đo JSON validity, extraction/risk/missing metrics, latency, fallback và số lượt gọi ước tính.
