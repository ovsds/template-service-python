import contextvars
import dataclasses
import logging
import re
import uuid

import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web

REQUEST_ID_HEADER = "X-Request-ID"
# Incoming IDs end up in logs and response headers, anything else is replaced to avoid log forging
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,128}")
_REQUEST_ID_KEY = aiohttp_web.RequestKey("request_id", str)


@dataclasses.dataclass(frozen=True)
class RequestContext:
    request_id: str


_request_context_var: contextvars.ContextVar[RequestContext | None] = contextvars.ContextVar(
    "request_context",
    default=None,
)


def get_request_context() -> RequestContext | None:
    return _request_context_var.get()


def _get_request_id(request: aiohttp_web.Request) -> str:
    request_id = request.headers.get(REQUEST_ID_HEADER)
    if request_id is not None and _REQUEST_ID_PATTERN.fullmatch(request_id):
        return request_id
    return uuid.uuid4().hex


@dataclasses.dataclass(frozen=True)
class RequestContextMiddleware:
    @aiohttp_web.middleware
    async def process(
        self,
        request: aiohttp_web.Request,
        handler: aiohttp_typedefs.Handler,
    ) -> aiohttp_web.StreamResponse:
        request_id = _get_request_id(request)
        request[_REQUEST_ID_KEY] = request_id
        token = _request_context_var.set(RequestContext(request_id=request_id))
        try:
            return await handler(request)
        finally:
            _request_context_var.reset(token)


async def set_response_request_id(
    request: aiohttp_web.Request,
    response: aiohttp_web.StreamResponse,
) -> None:
    # on_response_prepare runs for every prepared response: returned, streamed by the handler
    # or raised as aiohttp HTTP exception
    request_id = request.get(_REQUEST_ID_KEY)
    if request_id is not None:
        response.headers[REQUEST_ID_HEADER] = request_id


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
    "set_response_request_id",
]
