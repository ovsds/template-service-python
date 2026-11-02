import asyncio
import dataclasses
import http
import time

import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web
import prometheus_client

# Not found and method not allowed requests match no route
UNMATCHED_ROUTE = "unmatched"
# The client closed the connection before the response, as nginx reports it
CLIENT_CLOSED_REQUEST_STATUS = 499


@dataclasses.dataclass(frozen=True)
class RequestMetrics:
    registry: prometheus_client.CollectorRegistry

    requests_total: prometheus_client.Counter = dataclasses.field(init=False)
    request_duration_seconds: prometheus_client.Histogram = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "requests_total",
            prometheus_client.Counter(
                name="http_requests_total",
                documentation="HTTP requests handled",
                labelnames=["method", "route", "status"],
                registry=self.registry,
            ),
        )
        object.__setattr__(
            self,
            "request_duration_seconds",
            prometheus_client.Histogram(
                name="http_request_duration_seconds",
                documentation="HTTP request duration in seconds",
                labelnames=["method", "route"],
                registry=self.registry,
            ),
        )


@dataclasses.dataclass(frozen=True)
class RequestMetricsMiddleware:
    metrics: RequestMetrics

    @aiohttp_web.middleware
    async def process(
        self,
        request: aiohttp_web.Request,
        handler: aiohttp_typedefs.Handler,
    ) -> aiohttp_web.StreamResponse:
        started_at = time.perf_counter()
        status: int = http.HTTPStatus.INTERNAL_SERVER_ERROR
        try:
            response = await handler(request)
            status = response.status
            return response
        except aiohttp_web.HTTPException as exc:
            status = exc.status
            raise
        except asyncio.CancelledError:
            status = CLIENT_CLOSED_REQUEST_STATUS
            raise
        finally:
            # Route templates, not raw paths, keep label cardinality bounded
            route = self._get_route(request)
            self.metrics.requests_total.labels(method=request.method, route=route, status=str(status)).inc()
            self.metrics.request_duration_seconds.labels(method=request.method, route=route).observe(
                time.perf_counter() - started_at
            )

    def _get_route(self, request: aiohttp_web.Request) -> str:
        resource = request.match_info.route.resource
        if resource is None:
            return UNMATCHED_ROUTE
        return resource.canonical


@dataclasses.dataclass(frozen=True)
class MetricsHandler:
    registry: prometheus_client.CollectorRegistry

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        return aiohttp_web.Response(
            body=prometheus_client.generate_latest(self.registry),
            headers={"Content-Type": prometheus_client.CONTENT_TYPE_LATEST},
        )


__all__ = [
    "MetricsHandler",
    "RequestMetrics",
    "RequestMetricsMiddleware",
]
