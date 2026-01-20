"""
FastAPI Server
==============
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from redis_service.redis_client import get_redis_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("🚀 Starting similarity search service...")
    
    try:
        settings = get_settings()
        
        # Initialize Redis
        redis_client = get_redis_client(settings)
        app.state.redis_client = redis_client
        logger.info("✓ Redis client initialized")
        
        # Store settings
        app.state.settings = settings
        
        logger.info("✅ Service startup complete")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down service...")
    if hasattr(app.state, 'redis_client'):
        app.state.redis_client.disconnect()


# Initialize FastAPI app
app = FastAPI(
    title="Privacy-Preserving Image Similarity Search",
    description="FHE-based secure image similarity search service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Privacy-Preserving Image Similarity Search",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    redis_ok = False
    
    if hasattr(app.state, 'redis_client'):
        redis_ok = app.state.redis_client.ping()
    
    return {
        "status": "healthy" if redis_ok else "degraded",
        "redis_connected": redis_ok,
        "azure_connected": True,  # TODO: Add actual check
        "fhe_context_loaded": True  # TODO: Add actual check
    }


# Import and include routes
try:
    from api.routes import router
    app.include_router(router, prefix="/api/v1", tags=["search"])
    logger.info("✓ API routes loaded")
except ImportError as e:
    logger.warning(f"⚠ Routes not loaded: {e}")
