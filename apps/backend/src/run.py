import uvicorn
from .config import settings  # ensures .env is loaded

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=(settings.ENV == "development")
    )
