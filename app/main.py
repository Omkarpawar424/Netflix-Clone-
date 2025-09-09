"""
Main FastAPI application for the Forest Rights Act (FRA) Decision Support System
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, documents, gis, analytics, schemes, users
from app.ai_models.model_manager import ModelManager

# Global model manager instance
model_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global model_manager
    
    # Startup
    print("🚀 Starting FRA Decision Support System...")
    
    # Initialize database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize AI models
    model_manager = ModelManager()
    await model_manager.initialize_models()
    
    # Store model manager in app state
    app.state.model_manager = model_manager
    
    print("✅ System initialization complete!")
    
    yield
    
    # Shutdown
    print("🔄 Shutting down FRA Decision Support System...")
    if model_manager:
        await model_manager.cleanup()
    print("✅ Shutdown complete!")

# Create FastAPI application
app = FastAPI(
    title="FRA Decision Support System & WebGIS Platform",
    description="""
    AI-powered comprehensive Decision Support System (DSS) and WebGIS platform for 
    Forest Rights Act (FRA) implementation across multiple Indian states.
    
    ## Key Features
    
    * **Document Processing**: AI-powered digitization of legacy FRA documents
    * **Satellite Analysis**: Computer vision for land-use classification
    * **WebGIS Platform**: Interactive mapping and spatial analysis
    * **Decision Support**: Intelligent recommendations and cross-referencing
    * **Multi-State Coverage**: Support for MP, Tripura, Odisha, and Telangana
    """,
    version="1.0.0",
    contact={
        "name": "FRA DSS Development Team",
        "email": "support@fra-dss.gov.in",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Document Processing"])
app.include_router(gis.router, prefix="/api/v1/gis", tags=["GIS & Mapping"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics & Reporting"])
app.include_router(schemes.router, prefix="/api/v1/schemes", tags=["Government Schemes"])
app.include_router(users.router, prefix="/api/v1/users", tags=["User Management"])

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Forest Rights Act Decision Support System & WebGIS Platform",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "AI-Powered Document Processing",
            "Satellite Imagery Analysis",
            "Interactive WebGIS Platform",
            "Decision Support System",
            "Multi-State Implementation"
        ],
        "documentation": "/docs",
        "api_version": "v1"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "ai_models": "loaded" if model_manager and model_manager.models_loaded else "loading",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@app.get("/api/v1/system/info")
async def system_info(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get system information and statistics"""
    return {
        "system": {
            "name": "FRA Decision Support System",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "local"
        },
        "ai_models": {
            "document_processing": model_manager.is_model_loaded("document_ner") if model_manager else False,
            "satellite_analysis": model_manager.is_model_loaded("land_classifier") if model_manager else False,
            "computer_vision": model_manager.is_model_loaded("asset_detector") if model_manager else False
        },
        "supported_states": [
            "Madhya Pradesh",
            "Tripura", 
            "Odisha",
            "Telangana"
        ],
        "data_layers": [
            "Forest Cover",
            "Agricultural Land",
            "Water Bodies",
            "Village Boundaries",
            "Infrastructure",
            "FRA Claims",
            "Community Assets"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )