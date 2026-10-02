"""Common request ID and error envelope for the optional FastAPI services."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def install_http_contract(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id(request: Request, call_next):
        value = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = value
        response = await call_next(request)
        response.headers["X-Request-ID"] = value
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail), "request_id": request.state.request_id}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": "request validation failed", "request_id": request.state.request_id}},
        )

    @app.exception_handler(Exception)
    async def internal_error(request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "internal service error", "request_id": request.state.request_id}},
        )
