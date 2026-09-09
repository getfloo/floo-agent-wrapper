from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.errors import APIError, handle_api_error
from app.routes.projects import router
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings if settings is not None else Settings()
        yield

    app = FastAPI(title="floo agent wrapper", version="1.0.0", lifespan=lifespan)
    app.add_exception_handler(APIError, handle_api_error)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Match floo: do not echo request inputs (which can contain file secrets).
        errors = [{k: v for k, v in item.items() if k != "input"} for item in exc.errors()]
        return JSONResponse(status_code=422, content=jsonable_encoder({"detail": errors}))

    @app.exception_handler(ValidationError)
    async def upstream_validation_error(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=502,
            content={
                "detail": {
                    "code": "INVALID_UPSTREAM_RESPONSE",
                    "message": "Upstream returned an invalid response.",
                }
            },
        )

    @app.middleware("http")
    async def no_store(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()
