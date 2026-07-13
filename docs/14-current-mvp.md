# Current MVP — SOSFlow

Implemented: FastAPI/SQLAlchemy/PostgreSQL-or-SQLite flow, priority engine with aging, admin dashboard, simulated multi-source intake/duplicate candidates, explainable team recommendation, mission audit, installable static-build PWA reporter queue, silent-zone verification signals and an autoplay Trà Linh demo controller.

Demo accounts: none. MVP has no authentication or production authorization layer; Reporter, Dashboard and Rescue routes are open for local demonstration only.

Bedrock: `AI_PROVIDER=mock` is default. Use `AI_PROVIDER=bedrock` only with IAM default credential chain, region and a permitted model/profile/custom ARN. A Bedrock failure falls back when enabled; the repository has no trained/custom model claim unless a real custom ARN is configured.

AWS deployment: use an IAM role (not static keys in `.env`), managed PostgreSQL/RDS or an equivalent PostgreSQL service, TLS/reverse proxy, private networking and an object store/CDN only after attachment requirements are implemented. Run Alembic before rolling the API. This repository does not contain a production Terraform/CDK deployment yet.

Known limitations: SMS, Zalo, 112 and What3words are simulators only; silent zone means “verify contact”, not “incident confirmed”; straight-line recommendation distance is not ETA; photo attachments, audio transcription and Background Sync API are not implemented. Admin/rescue authentication is also intentionally absent from this local MVP, so it must not be exposed as a production system unchanged.
