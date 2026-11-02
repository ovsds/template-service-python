import dataclasses

import aiohttp.test_utils as aiohttp_test_utils
import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web
import prometheus_client
import pytest

import lib.utils.aiohttp as aiohttp_utils

Client = aiohttp_test_utils.TestClient[aiohttp_web.Request, aiohttp_web.Application]


@dataclasses.dataclass(frozen=True)
class ItemHandler:
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        return aiohttp_utils.Response.with_data(data={"item_id": request.match_info["item_id"]})


@dataclasses.dataclass(frozen=True)
class RedirectHandler:
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise aiohttp_web.HTTPFound(location="/items/1")


@dataclasses.dataclass(frozen=True)
class FailingHandler:
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise RuntimeError("Unexpected failure")


@dataclasses.dataclass(frozen=True)
class MetricsAppFactory(aiohttp_utils.AppFactory):
    request_metrics: aiohttp_utils.RequestMetrics

    def get_routes(self) -> list[aiohttp_utils.Route]:
        return [
            aiohttp_utils.Route(method="GET", path="/items/{item_id}", handler=ItemHandler()),
            aiohttp_utils.Route(method="GET", path="/redirect", handler=RedirectHandler()),
            aiohttp_utils.Route(method="GET", path="/failure", handler=FailingHandler()),
            aiohttp_utils.Route(
                method="GET",
                path="/metrics",
                handler=aiohttp_utils.MetricsHandler(registry=self.request_metrics.registry),
            ),
        ]

    def get_middlewares(self) -> list[aiohttp_typedefs.Middleware]:
        request_metrics_middleware = aiohttp_utils.RequestMetricsMiddleware(metrics=self.request_metrics)
        return [request_metrics_middleware.process, *super().get_middlewares()]


def create_client(registry: prometheus_client.CollectorRegistry) -> Client:
    app = MetricsAppFactory(request_metrics=aiohttp_utils.RequestMetrics(registry=registry)).create()
    return aiohttp_test_utils.TestClient(aiohttp_test_utils.TestServer(app))


def get_requests_total(registry: prometheus_client.CollectorRegistry, route: str, status: str) -> float | None:
    return registry.get_sample_value(
        "http_requests_total",
        labels={"method": "GET", "route": route, "status": status},
    )


@pytest.mark.asyncio
async def test_counts_requests_by_route_template():
    registry = prometheus_client.CollectorRegistry()
    async with create_client(registry) as client:
        await client.get("/items/1")
        await client.get("/items/2")

    assert get_requests_total(registry, route="/items/{item_id}", status="200") == 2
    duration_count = registry.get_sample_value(
        "http_request_duration_seconds_count",
        labels={"method": "GET", "route": "/items/{item_id}"},
    )
    assert duration_count == 2


@pytest.mark.asyncio
async def test_counts_unmatched_route():
    registry = prometheus_client.CollectorRegistry()
    async with create_client(registry) as client:
        response = await client.get("/missing")

        assert response.status == 404

    assert get_requests_total(registry, route="unmatched", status="404") == 1


@pytest.mark.asyncio
async def test_counts_raised_http_exception():
    registry = prometheus_client.CollectorRegistry()
    async with create_client(registry) as client:
        response = await client.get("/redirect", allow_redirects=False)

        assert response.status == 302

    assert get_requests_total(registry, route="/redirect", status="302") == 1


@pytest.mark.asyncio
async def test_counts_unhandled_error():
    registry = prometheus_client.CollectorRegistry()
    async with create_client(registry) as client:
        response = await client.get("/failure")

        assert response.status == 500

    assert get_requests_total(registry, route="/failure", status="500") == 1


@pytest.mark.asyncio
async def test_metrics_handler():
    registry = prometheus_client.CollectorRegistry()
    async with create_client(registry) as client:
        await client.get("/items/1")
        response = await client.get("/metrics")

        assert response.status == 200
        assert response.content_type == "text/plain"
        assert 'http_requests_total{method="GET",route="/items/{item_id}",status="200"} 1.0' in await response.text()
