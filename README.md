# AI Sales Agent - Setup Guide

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Google Cloud Project (for Calendar API)
- SendGrid Account
- Slack Workspace (for notifications)

## Installation

### 1. Clone and Setup Environment
```bash
# Create virtual environment in backend directory
python -m venv ai-agent-venv
source ai-agent-venv /bin/activate  # On Windows: venv\Scripts\activate

# Install poetry
pip install poetry

# Install dependencies
poetry install
```

### 2. Database Setup
```bash
# Create PostgreSQL database
createdb ai_sales_agent

# Run migrations
alembic upgrade head
```

### 3. Redis Setup
```bash
# Start Redis (if not running)
redis-server

# Test connection
redis-cli ping  # Should return PONG
```

### 4. Google Calendar API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Enable "Google Calendar API"
4. Create Service Account:
   - Go to "Credentials" → "Create Credentials" → "Service Account"
   - Download JSON key file
   - Save as `credentials/google-calendar-service-account.json`
5. Share your Google Calendar with the service account email

### 5. SendGrid Setup

1. Sign up at [SendGrid](https://sendgrid.com)
2. Create API Key (Settings → API Keys)
3. Verify sender email
4. Add API key to `.env`

### 6. Slack Webhook Setup

1. Go to [Slack API](https://api.slack.com/messaging/webhooks)
2. Create new Incoming Webhook
3. Select channel for notifications
4. Copy webhook URL to `.env`

### 7. Environment Configuration
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

## Running the Application
```bash
# Development mode with auto-reload
uvicorn src.run:app --reload --port 8000

# Production mode
uvicorn src.run:app --host 0.0.0.0 --port 8000 --workers 4
```

## Testing
```bash
# Run tests
pytest

# Test WebSocket connection
wscat -c ws://localhost:8000/ws/chat/test-visitor-123

# Send test message
{"message": "I need a mobile app"}
```

## API Endpoints

- `GET /` - Health check
- `WS /ws/chat/{visitor_id}` - WebSocket chat endpoint
- `GET /api/conversations` - List conversations (admin)
- `GET /api/leads` - List leads (admin)

## Cost Estimation

Per 1000 conversations:
- OpenAI (gpt-4o): ~$15-30
- SendGrid: Free tier (100 emails/day)
- Google Calendar: Free
- Slack: Free
- **Total: ~$0.015-0.03 per conversation**

## Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL is running
pg_isready

# Check connection string in .env
DATABASE_URL=postgresql://user:pass@localhost:5432/ai_sales_agent
```

### Redis Connection Failed
```bash
# Check Redis is running
redis-cli ping

# Check connection in .env
REDIS_URL=redis://localhost:6379/0
```

### Google Calendar API Not Working
- Verify service account JSON file path
- Check calendar is shared with service account email
- Ensure Calendar API is enabled in Google Cloud Console

## Production Deployment

See `DEPLOYMENT.md` for Docker, AWS, and scaling instructions.

## Support

For issues, contact: dev@accellionx.com


```bash
cd apps/backend && python3 -m venv ai-agent-venv
source ai-agent-venv/bin/activate 
RUN. nodemon --exec "python3 -m src.run" --ext py
```