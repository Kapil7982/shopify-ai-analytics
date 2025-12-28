"""
Shopify AI Analytics - Python AI Service
Main FastAPI application entry point
"""
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.api.demo_routes import router as demo_router
from app.api.gateway_routes import router as gateway_router
from app.api.realdata_routes import router as realdata_router
from app.core.config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

app = FastAPI(
    title="Shopify AI Analytics Service",
    description="AI-powered analytics service for Shopify stores using LLM and ShopifyQL",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")
app.include_router(gateway_router, prefix="/api/v1", tags=["Gateway (Rails API Simulation)"])
app.include_router(realdata_router, prefix="/api/v1", tags=["Real Data (Direct Shopify API)"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "shopify-ai-analytics",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Shopify AI Analytics Service")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Shopify AI Analytics Service")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
