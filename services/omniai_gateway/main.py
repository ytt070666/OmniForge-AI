from __future__ import annotations

import argparse

import uvicorn

from .settings import load_gateway_settings


def main() -> int:
    settings = load_gateway_settings()
    parser = argparse.ArgumentParser(description="Run the OmniAI FastAPI gateway")
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("services.omniai_gateway.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
