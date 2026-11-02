import dataclasses
import http
import logging
import time

import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class RequestLoggingMiddleware:
    @aiohttp_web.middleware
    async def process(
        self,
        request: aiohttp_web.Request,
        handler: aiohttp_typedefs.Handler,
    ) -> aiohttp_web.StreamResponse:
        start_time = time.perf_counter()
        # Error middleware turns exceptions into responses, only unmapped aiohttp HTTP exceptions and
        # cancellations get here
        status: int = http.HTTPStatus.INTERNAL_SERVER_ERROR
        try:
            response = await handler(request)
            status = response.status
            return response
        except aiohttp_web.HTTPException as exc:
            status = exc.status
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "Request has been processed: method=%s path=%s status=%s duration_ms=%.3f",
                request.method,
                request.path,
                status,
                duration_ms,
            )


__all__ = [
    "RequestLoggingMiddleware",
]
