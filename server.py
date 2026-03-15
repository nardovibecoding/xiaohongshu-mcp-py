"""XHS MCP Server — FastAPI + MCP on same port via uvicorn."""

import argparse
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from browser_manager import get_browser
from api_routes import router as api_router
from mcp_tools import mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("xhs.server")

# Headless flag — set by CLI args before app starts
_headless = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting browser...")
    bm = await get_browser()
    await bm.start(headless=_headless)
    logger.info("Browser ready")
    yield
    # Shutdown
    logger.info("Shutting down browser...")
    bm = await get_browser()
    await bm.stop()
    logger.info("Browser stopped")


# FastAPI app
app = FastAPI(title="XHS MCP Server (Patchright)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API routes
app.include_router(api_router)


# Health check
@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


# Mount MCP streamable HTTP handler — mcp_app has its own /mcp route,
# so mount at root so endpoint is at /mcp
mcp_app = mcp.streamable_http_app()
app.mount("/", mcp_app)


def main():
    global _headless
    parser = argparse.ArgumentParser(description="XHS MCP Server (Patchright)")
    parser.add_argument("--port", type=int, default=18060, help="Server port (default: 18060)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless (default)")
    parser.add_argument("--no-headless", action="store_true", help="Run browser with GUI")
    args = parser.parse_args()

    if args.no_headless:
        _headless = False

    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
