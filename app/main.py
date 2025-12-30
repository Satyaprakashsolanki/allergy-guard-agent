from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.database import engine, Base
from app.routers import auth, users, allergens, analysis, questions
from app.services.seed_data import seed_allergens
from app.core.database import AsyncSessionLocal

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    print("🚀 Starting AllergyGuard API...")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")

    # Seed allergen data
    async with AsyncSessionLocal() as session:
        await seed_allergens(session)

    yield

    # Shutdown
    print("👋 Shutting down AllergyGuard API...")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Allergy Risk Decision Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
# Development: Allow localhost origins for testing
# Production: Use CORS_ORIGINS from environment variable or restrict to specific domains
DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8081",
    "http://10.0.2.2:8081",  # Android emulator
    "http://127.0.0.1:8081",
]

# In production, CORS_ORIGINS should be set via environment variable
# e.g., CORS_ORIGINS="https://yourapp.com,https://api.yourapp.com"
# If not set, production defaults to restrictive mode (no wildcard)
def get_cors_origins():
    if settings.DEBUG or settings.ENVIRONMENT == "development":
        return DEV_ORIGINS
    # Production: use configured origins or empty list (no CORS)
    if settings.CORS_ORIGINS and settings.CORS_ORIGINS != ["*"]:
        return settings.CORS_ORIGINS
    # SECURITY: Don't allow wildcard in production - log warning
    import logging
    logging.warning("CORS_ORIGINS not configured for production - using restrictive defaults")
    return []  # Restrictive by default in production

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "Welcome to AllergyGuard API",
        "version": settings.APP_VERSION,
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(allergens.router, prefix="/api/v1/allergens", tags=["Allergens"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(questions.router, prefix="/api/v1/questions", tags=["Questions"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
