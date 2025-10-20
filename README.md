# ai-sales-agent-bk

Backend for an AI Sales Agent (FastAPI) with OpenAI function calling, Redis conversation state, Postgres leads, and optional integrations (Calendar/Email/CRM/Slack).

## Quick start
```bash
cp .env.example apps/backend/.env   # fill OPENAI_API_KEY at minimum
cd infra && docker compose up --build
```

Test:
```bash
curl -X POST http://localhost:80/chat   -H "Content-Type: application/json"   -d '{"visitor_id":"demo-123","message":"I need a mobile app for my clothing store"}'
```

## work in enviroment
```bash
cd apps/backend && python3 -m venv ai-agent-venv
source ai-agent-venv/bin/activate 
RUN. nodemon --exec "python3 -m src.run" --ext py
```