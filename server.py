"""XHS MCP Server — FastAPI + MCP on same port via uvicorn."""

import argparse
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response
from starlette.requests import Request

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

# Build MCP app first (creates session manager internally), then grab session manager
_mcp_starlette_app = mcp.streamable_http_app()
_session_manager = mcp.session_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup browser
    logger.info("Starting browser...")
    bm = await get_browser()
    await bm.start(headless=_headless)
    logger.info("Browser ready")

    # Start MCP session manager (required for /mcp endpoint)
    async with _session_manager.run():
        logger.info("MCP session manager started")
        yield

    # Shutdown browser
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


# MCP endpoint — forward to session manager via ASGI
@app.api_route("/mcp", methods=["GET", "POST", "DELETE"])
async def mcp_handler(request: Request):
    """Forward MCP protocol requests to session manager."""
    response_body = []
    response_headers = []
    status_code = 200

    async def receive():
        body = await request.body()
        return {"type": "http.request", "body": body}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
            response_headers.extend(message.get("headers", []))
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    scope = dict(request.scope)
    scope["path"] = "/mcp"

    await _session_manager.handle_request(scope, receive, send)

    headers = {}
    for k, v in response_headers:
        key = k.decode() if isinstance(k, bytes) else k
        val = v.decode() if isinstance(v, bytes) else v
        headers[key] = val

    return Response(
        content=b"".join(response_body),
        status_code=status_code,
        headers=headers,
    )


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
