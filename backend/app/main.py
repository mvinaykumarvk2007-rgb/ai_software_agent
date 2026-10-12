import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router

app = FastAPI(
    title="AI Software Engineering Assistant API",
    version="1.0.0",
    description="Backend service providing project validation and workflow orchestration endpoints."
)

DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(DEFAULT_ORIGINS)).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials="*" not in ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Register API routes with /api prefix
app.include_router(api_router, prefix="/api")


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "AI Software Engineering Assistant Backend",
        "health": "/api/health",
        "docs": "/docs"
    }
