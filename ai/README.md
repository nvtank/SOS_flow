# SOSFlow AI assets

The website runtime source of truth is `backend/app/services/ai_analyzer.py`. It implements the validated Amazon Bedrock Converse tool output and the safe mock fallback used by the FastAPI intake pipeline.

This directory also contains an optional standalone CLI/prioritization toolkit. Run it from the repository root with `python -m ai.bedrock_cli --mode mock`. Its environment aliases match the web runtime: `AI_PROVIDER`, `AWS_REGION`, `BEDROCK_MODEL_ID`, and `BEDROCK_INFERENCE_PROFILE_ARN`.

The synthetic datasets contain no real personal information. Run the web analyzer baseline with:

```bash
python scripts/evaluate_analyzer.py --provider mock
python scripts/evaluate_analyzer.py --provider bedrock  # makes paid invocations
```

The example training/validation files are readiness artifacts only. This repository does not start a customization or fine-tuning job and does not claim a trained custom model.
