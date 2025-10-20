from sqlite3 import OperationalError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api.routes_health import router as health_router
from .api.routes_chat import router as chat_router
from .api.routes_chat_ws import router as chat_ws_router
from .models import create_all

# Create FastAPI app
app = FastAPI(
    title="AI Sales Agent API",
    version="1.0.0",
    description="Autonomous AI sales agent backend with conversation, lead scoring, and automation tools."
)

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000", "https://yourfrontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(chat_ws_router)

# Database setup on startup
@app.on_event("startup")
def startup():
    print("🚀 Starting up AI Sales Agent API...")
    print(f"🌐 Environment: {settings.ENV}")
    # Auto-create tables if they don’t exist
    try:
        create_all()
    except OperationalError as e:
        raise RuntimeError("❌ Database connection failed. Check DATABASE_URL and credentials.") from e

# Base route
@app.get("/")
def root():
    return {
        "name": "AI Sales Agent API",
        "env": settings.ENV,
        "status": "running",
        "docs_url": "/docs"
    }
