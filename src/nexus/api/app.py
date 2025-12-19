"""
FastAPI Application.

Main entry point for the Nexus web API.
"""

from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from nexus._version import __version__
from nexus.config import NexusConfig, get_config

if TYPE_CHECKING:
    from nexus.channels.manager import ChannelManager
    from nexus.core.router import Router
    from nexus.fleet.manager import FleetManager

logger = logging.getLogger(__name__)


class NexusAPI:
    """
    Nexus API application wrapper.

    Manages FastAPI app, components, and lifecycle.
    """

    def __init__(
        self,
        config: NexusConfig | None = None,
        router: "Router | None" = None,
        channel_manager: "ChannelManager | None" = None,
        fleet_manager: "FleetManager | None" = None,
    ) -> None:
        self._config = config or get_config()
        self._router = router
        self._channel_manager = channel_manager
        self._fleet_manager = fleet_manager

        # Generate API key if not configured
        self._api_key = self._config.server.api_key or secrets.token_urlsafe(32)

        # Create FastAPI app
        self._app = self._create_app()

    @property
    def app(self) -> FastAPI:
        """Get FastAPI app instance."""
        return self._app

    @property
    def api_key(self) -> str:
        """Get API key."""
        return self._api_key

    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        app = FastAPI(
            title="MoMo-Nexus API",
            description="Central Communication Hub for MoMo Ecosystem",
            version=__version__,
            docs_url="/docs" if not self._config.server.auth_enabled else None,
            redoc_url="/redoc" if not self._config.server.auth_enabled else None,
        )

        # Store references in app state
        app.state.nexus = self
        app.state.config = self._config
        app.state.router = self._router
        app.state.channel_manager = self._channel_manager
        app.state.fleet_manager = self._fleet_manager
        app.state.api_key = self._api_key

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self._config.server.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add exception handler
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            logger.error(f"Unhandled error: {exc}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "detail": str(exc)},
            )

        # Import and include routes
        from nexus.api.routes import router as api_router
        from nexus.api.websocket import router as ws_router
        from nexus.api.sync import sync_router

        app.include_router(api_router, prefix="/api")
        app.include_router(sync_router, prefix="/api")
        app.include_router(ws_router)

        # Mount static files for dashboard
        dashboard_path = Path(__file__).parent / "dashboard"
        if dashboard_path.exists():
            app.mount("/", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")

        # Root redirect
        @app.get("/", include_in_schema=False)
        async def root():
            return {"message": "MoMo-Nexus API", "version": __version__, "docs": "/docs"}

        return app

    async def start(self) -> None:
        """Start the API server."""
        import uvicorn

        config = uvicorn.Config(
            app=self._app,
            host=self._config.server.host,
            port=self._config.server.port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()


def create_app(
    config: NexusConfig | None = None,
    router: "Router | None" = None,
    channel_manager: "ChannelManager | None" = None,
    fleet_manager: "FleetManager | None" = None,
) -> FastAPI:
    """
    Create FastAPI application.

    Factory function for creating the Nexus API.
    """
    api = NexusAPI(
        config=config,
        router=router,
        channel_manager=channel_manager,
        fleet_manager=fleet_manager,
    )
    return api.app

