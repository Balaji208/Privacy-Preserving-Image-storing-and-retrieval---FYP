"""
Application Entry Point
=======================

Runs the FastAPI server with Uvicorn.
"""

import uvicorn
from config.settings import get_settings


def main():
    """Run the application server."""
    settings = get_settings()
    
    uvicorn.run(
        "api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        timeout_keep_alive=settings.api_timeout,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
