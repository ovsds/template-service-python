import contextvars
import dataclasses
import logging
import uuid

import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web

REQUEST_ID_HEADER = "X-Request-ID"


@dataclasses.dataclass(frozen=True)
class RequestContext:
    request_id: str


_request_context_var: contextvars.ContextVar[RequestContext | None] = contextvars.ContextVar(
    "request_context",
    default=None,
)


def get_request_context() -> RequestContext | None:
    return _request_context_var.get()


@dataclasses.dataclass(frozen=True)
class RequestContextMiddleware:
    @aiohttp_web.middleware
    async def process(
        self,
        request: aiohttp_web.Request,
        handler: aiohttp_typedefs.Handler,
    ) -> aiohttp_web.StreamResponse:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = _request_context_var.set(RequestContext(request_id=request_id))
        try:
            response = await handler(request)
        except aiohttp_web.HTTPException as exc:
            # Unmapped aiohttp HTTP exceptions are rendered by aiohttp itself, so they carry the header too
            exc.headers[REQUEST_ID_HEADER] = request_id
            raise
        finally:
            _request_context_var.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class RequestContextLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_context = get_request_context()
        record.request_id = request_context.request_id if request_context is not None else "-"
        return True


__all__ = [
    "REQUEST_ID_HEADER",
    "RequestContext",
    "RequestContextLogFilter",
    "RequestContextMiddleware",
    "get_request_context",
]
