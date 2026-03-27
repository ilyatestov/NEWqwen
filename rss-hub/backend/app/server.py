"""
FastAPI application with static file serving for the frontend.
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .api.routes import app as api_app
from .core.config import get_config

# Create main app
app = FastAPI(
    title="RSS Hub",
    description="Complete RSS to Telegram platform with web dashboard",
    version="2.0.0"
)

# Mount API routes
app.mount("/api", api_app)

# Serve frontend
frontend_path = Path(__file__).parent.parent.parent / "frontend"


@app.get("/")
async def serve_frontend():
    """Serve the main frontend application."""
    return FileResponse(frontend_path / "index.html")


@app.get("/{path:path}")
async def serve_frontend_assets(path: str):
    """Serve frontend assets or fallback to index.html for SPA routing."""
    asset_path = frontend_path / path
    
    # Check if it's a static asset
    if asset_path.exists() and asset_path.is_file():
        return FileResponse(asset_path)
    
    # Otherwise return index.html (for Vue router)
    return FileResponse(frontend_path / "index.html")


if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run(
        "backend.app.server:app",
        host=config.web.host,
        port=config.web.port,
        reload=config.web.debug
    )
