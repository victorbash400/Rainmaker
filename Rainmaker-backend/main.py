"""
Rainmaker FastAPI Application Entry Point
"""

import asyncio
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager

# Fix for Windows Playwright subprocess issue - MUST be set before any asyncio operations
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.core.config import settings
from app.api.v1 import prospects, campaigns, conversations, proposals, meetings, auth, campaign_planning, browser_viewer, enrichment_viewer, outreach
from app.db.session import engine
from app.db import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Rainmaker API...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    
    # Setup browser viewer
    try:
        from app.api.v1.browser_viewer import setup_browser_viewer
        print("🔧 Setting up browser viewer callbacks...")
        setup_browser_viewer()
        print("✅ Browser viewer callbacks configured")
    except Exception as e:
        print(f"❌ Failed to setup browser viewer: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Setup enrichment viewer
    try:
        from app.api.v1.enrichment_viewer import setup_enrichment_viewer
        from app.agents.enrichment import set_enrichment_viewer_callback
        from app.api.v1.enrichment_viewer import enrichment_viewer_callback
        
        print("🔧 Setting up enrichment viewer callbacks...")
        setup_enrichment_viewer()
        set_enrichment_viewer_callback(enrichment_viewer_callback)
        print("✅ Enrichment viewer callbacks configured")
    except Exception as e:
        print(f"❌ Failed to setup enrichment viewer: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("✅ Database tables created")
    print("✅ Browser viewer initialized")
    print("✅ Enrichment viewer initialized")
    print(f"🌐 API running on http://localhost:8000")
    print(f"📚 Documentation available at http://localhost:8000/docs")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Rainmaker API...")


# Create FastAPI application
app = FastAPI(
    title="Rainmaker API",
    description="AI-powered event planning sales assistant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(prospects.router, prefix="/api/v1/prospects", tags=["prospects"])
app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["conversations"])
app.include_router(proposals.router, prefix="/api/v1/proposals", tags=["proposals"])
app.include_router(meetings.router, prefix="/api/v1/meetings", tags=["meetings"])
app.include_router(campaign_planning.router, prefix="/api/v1/campaign-planning", tags=["campaign-planning"])
app.include_router(browser_viewer.router, prefix="/api/v1/browser-viewer", tags=["browser-viewer"])
app.include_router(enrichment_viewer.router, prefix="/api/v1/enrichment-viewer", tags=["enrichment-viewer"])
app.include_router(outreach.router, prefix="/api/v1/outreach", tags=["outreach"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Rainmaker API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "rainmaker-api",
        "version": "1.0.0"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "success": False
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "success": False
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )