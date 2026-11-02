import dataclasses
import http
import logging
import typing

import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web

import lib.utils.aiohttp.handlers.base as handlers_base

logger = logging.getLogger(__name__)


class BadRequestResponseSchema(handlers_base.ErrorResponseSchema):
    code: str = "BAD_REQUEST"
    message: str = "Bad request"
    status_code: int = http.HTTPStatus.BAD_REQUEST


class NotFoundResponseSchema(handlers_base.ErrorResponseSchema):
    code: str = "NOT_FOUND"
    message: str = "Not found"
    status_code: int = http.HTTPStatus.NOT_FOUND


class MethodNotAllowedResponseSchema(handlers_base.ErrorResponseSchema):
    code: str = "METHOD_NOT_ALLOWED"
    message: str = "Method not allowed"
    status_code: int = http.HTTPStatus.METHOD_NOT_ALLOWED


class InternalServerErrorResponseSchema(handlers_base.ErrorResponseSchema):
    code: str = "INTERNAL_SERVER_ERROR"
    message: str = "Internal server error"
    status_code: int = http.HTTPStatus.INTERNAL_SERVER_ERROR


DEFAULT_ERROR_MAP: typing.Mapping[type[Exception], handlers_base.ErrorResponseSchema] = {
    handlers_base.RequestValidationError: BadRequestResponseSchema(),
    aiohttp_web.HTTPNotFound: NotFoundResponseSchema(),
    aiohttp_web.HTTPMethodNotAllowed: MethodNotAllowedResponseSchema(),
}


@dataclasses.dataclass(frozen=True)
class ErrorHandlingMiddleware:
    error_map: typing.Mapping[type[Exception], handlers_base.ErrorResponseSchema]

    @aiohttp_web.middleware
    async def process(
        self,
        request: aiohttp_web.Request,
        handler: aiohttp_typedefs.Handler,
    ) -> aiohttp_web.StreamResponse:
        try:
            return await handler(request)
        except Exception as exc:
            schema = self._find_schema(exc)
            if schema is not None:
                return schema.as_error_response()
            # Unmapped aiohttp HTTP exceptions (redirects and the like) are valid responses, aiohttp renders them
            if isinstance(exc, aiohttp_web.HTTPException):
                raise
            logger.exception("Unhandled request error")
            return InternalServerErrorResponseSchema().as_error_response()

    def _find_schema(self, exc: Exception) -> handlers_base.ErrorResponseSchema | None:
        for exc_class in type(exc).__mro__:
            schema = self.error_map.get(exc_class)
            if schema is not None:
                return schema
        return None


__all__ = [
    "BadRequestResponseSchema",
    "ErrorHandlingMiddleware",
    "InternalServerErrorResponseSchema",
    "MethodNotAllowedResponseSchema",
    "NotFoundResponseSchema",
]
