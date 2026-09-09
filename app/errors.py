from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, status: int, body: Any):
        self.status = status
        self.body = body


def error(status: int, code: str, message: str, **extra: Any) -> APIError:
    # floo's raise_error uses FastAPI's {"detail": {"code", "message", ...}} envelope.
    return APIError(status, {"detail": {"code": code, "message": message, **extra}})


async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status, content=exc.body, headers={"Cache-Control": "no-store"}
    )
