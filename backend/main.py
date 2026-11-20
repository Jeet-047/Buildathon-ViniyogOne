"""
FastAPI Backend Entry Point for Viniyog ONE.
Google Startup-Buildathon Program.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import get_logger
from app.db.mongodb import get_mongo_db, seed_demo_data
from app.api.personas import router as personas_router
from app.api.chat import router as chat_router

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup & shutdown events.
    Seeds the 4 demo profiles into MongoDB Atlas on startup.
    """
    logger.info("=" * 70)
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"• LLM Provider     : {settings.LLM_PROVIDER} (Vertex AI via ADC)")
    logger.info(f"• Normal Model     : {settings.GOOGLE_NORMAL_MODEL}")
    logger.info(f"• Reasoning Model  : {settings.GOOGLE_REASONING_MODEL}")
    logger.info(f"• Vertex Location  : {settings.GOOGLE_VERTEX_LOCATION}")
    logger.info(f"• Database Target  : {settings.MONGO_DB_NAME} (Simulation={settings.MONGO_SIMULATION})")
    logger.info(f"• LangSmith Tracing: {'ENABLED (' + settings.LANGSMITH_PROJECT + ')' if settings.LANGSMITH_TRACING else 'DISABLED'}")
    logger.info("=" * 70)

    # Auto-seed MongoDB Atlas on server startup
    try:
        db = get_mongo_db()
        await seed_demo_data(db)
        logger.info("✓ MongoDB Atlas demo profiles verified on startup.")
    except Exception as exc:
        logger.warning(f"Could not verify MongoDB startup seed: {exc}")

    yield

    logger.info("Shutting down Viniyog ONE Backend service.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Behavior Intelligence & Financial Decision Engine API for Google Startup-Buildathon",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers directly
app.include_router(personas_router)
app.include_router(chat_router)


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root metadata endpoint."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
    }


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for Cloud Run and load balancers."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "simulation_mode": settings.MONGO_SIMULATION,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
