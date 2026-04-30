from fastapi import Request
from fastapi.responses import JSONResponse

from backend.utils.logger import get_logger

logger = get_logger("exceptions")


class AppException(Exception):
    def __init__(self, code: int, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error("AppException %d: %s", exc.code, exc.message)
    else:
        logger.warning("AppException %d: %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": 5000, "message": "Internal server error", "data": None},
    )
