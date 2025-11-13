"""
BHP Mooring Data Dashboard
Main application entry point with clean, modular architecture.
"""

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path

# Core imports
from app.core import setup_logging, get_settings, get_logger

# Service imports  
from app.services import (
    DataManagementService,
    TensionMonitoringService,
    MovementAnalysisService,
    CommunicationService
)

# API router imports
from app.api import dashboard, data, monitoring, movements, communication

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Get application settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    description="A comprehensive monitoring system for ship mooring operations"
)

# Setup static files and templates
if Path(settings.static_directory).exists():
    app.mount("/static", StaticFiles(directory=settings.static_directory), name="static")

templates = Jinja2Templates(directory=settings.template_directory)

# Initialize services
logger.info("Initializing services...")

data_service = DataManagementService()
tension_service = TensionMonitoringService()
movement_service = MovementAnalysisService()
communication_service = CommunicationService()

logger.info("Services initialized successfully")

# Initialize API routers with service dependencies
dashboard.init_services(data_service, tension_service, movement_service)
data.init_services(data_service)
monitoring.init_services(tension_service, data_service)
movements.init_services(movement_service, data_service)
communication.init_services(communication_service, data_service)

# Include routers
app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(data.router, tags=["Data"])
app.include_router(monitoring.router, tags=["Monitoring"])
app.include_router(movements.router, tags=["Movements"])
app.include_router(communication.router, tags=["Communication"])

logger.info("API routers configured successfully")


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Server running on http://{settings.host}:{settings.port}")
    logger.info("Dashboard available at: http://127.0.0.1:8000")
    logger.info("Generator should POST to: http://127.0.0.1:8000/")


@app.on_event("shutdown") 
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down application...")
    
    # Cleanup services if needed
    data_service.cleanup_old_data()
    
    logger.info("Application shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.version,
        "services": {
            "data_service": "active",
            "tension_service": "active", 
            "movement_service": "active",
            "communication_service": "active"
        }
    }


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("BHP MOORING DATA DASHBOARD")
    logger.info("=" * 60)
    logger.info("A comprehensive monitoring system for ship mooring operations")
    logger.info(f"Version: {settings.version}")
    logger.info("=" * 60)
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()