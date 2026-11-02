import dataclasses
import http
import time

import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web
import prometheus_client

UNMATCHED_ROUTE = "unmatched"


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
        try:
            response = await handler(request)
        except aiohttp_web.HTTPException as exc:
            self._observe(request, status=exc.status, started_at=started_at)
            raise
        except Exception:
            self._observe(request, status=http.HTTPStatus.INTERNAL_SERVER_ERROR, started_at=started_at)
            raise
        # A cancelled handler, at server shutdown, sent no response and is not counted
        self._observe(request, status=response.status, started_at=started_at)
        return response

    def _observe(self, request: aiohttp_web.Request, status: int, started_at: float) -> None:
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
