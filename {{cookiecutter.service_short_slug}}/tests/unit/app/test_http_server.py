import aiohttp.test_utils as aiohttp_test_utils
import aiohttp.web as aiohttp_web
{%- if cookiecutter.with_prometheus == "true" %}
import prometheus_client
{%- endif %}
import pytest

import lib.app.http_server as app_http_server
import lib.app.settings as app_settings
import lib.utils.aiohttp as aiohttp_utils

Client = aiohttp_test_utils.TestClient[aiohttp_web.Request, aiohttp_web.Application]


async def is_ready() -> bool:
    return True


def create_client() -> Client:
    readiness_service = aiohttp_utils.ReadinessService(
        subsystems=[aiohttp_utils.SubsystemReadinessCallback(name="database", is_ready=is_ready)],
    )
    app = app_http_server.HttpServerAppFactory(
        settings=app_settings.Settings(),
        readiness_service=readiness_service,
{%- if cookiecutter.with_prometheus == "true" %}
        request_metrics=aiohttp_utils.RequestMetrics(registry=prometheus_client.CollectorRegistry()),
{%- endif %}
    ).create()
    return aiohttp_test_utils.TestClient(aiohttp_test_utils.TestServer(app))


@pytest.mark.asyncio
async def test_liveness_probe():
    async with create_client() as client:
        response = await client.get("/health/liveness")

        assert response.status == 200
        assert await response.json() == {"status": "healthy"}


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/health/readiness", "/health/startup"])
async def test_subsystem_probe(path: str):
    async with create_client() as client:
        response = await client.get(path)

        assert response.status == 200
        assert await response.json() == {
            "status": "healthy",
            "subsystems_status": {"database": {"value": True, "required": True}},
        }


@pytest.mark.asyncio
async def test_app_info(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP__NAME", "test-service")
    monkeypatch.setenv("APP__VERSION", "1.2.3")

    async with create_client() as client:
        response = await client.get("/api/v1/info")

        assert response.status == 200
        assert await response.json() == {"name": "test-service", "version": "1.2.3"}


@pytest.mark.asyncio
async def test_openapi_spec(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP__NAME", "test-service")
    monkeypatch.setenv("APP__VERSION", "1.2.3")

    async with create_client() as client:
        response = await client.get("/api/v1/docs/spec.json")

        assert response.status == 200
        spec = await response.json()
        assert spec["info"] == {"title": "test-service", "version": "1.2.3"}
        assert {path: list(operations) for path, operations in spec["paths"].items()} == {
            "/health/liveness": ["get"],
            "/health/readiness": ["get"],
            "/health/startup": ["get"],
            "/api/v1/info": ["get"],
        }
        assert spec["paths"]["/api/v1/info"]["get"]["tags"] == ["app"]


@pytest.mark.asyncio
async def test_swagger_ui():
    async with create_client() as client:
        response = await client.get("/api/v1/docs")

        assert response.status == 200
        assert response.content_type == "text/html"
{%- if cookiecutter.with_prometheus == "true" %}


@pytest.mark.asyncio
async def test_metrics():
    async with create_client() as client:
        await client.get("/health/liveness")
        response = await client.get("/metrics")

        assert response.status == 200
        assert 'http_requests_total{method="GET",route="/health/liveness",status="200"} 1.0' in await response.text()
{%- endif %}
