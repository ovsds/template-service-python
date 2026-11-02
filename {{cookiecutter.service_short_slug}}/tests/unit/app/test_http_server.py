import aiohttp.test_utils as aiohttp_test_utils
import aiohttp.web as aiohttp_web
import pytest

import lib.app.http_server as app_http_server
import lib.app.settings as app_settings

Client = aiohttp_test_utils.TestClient[aiohttp_web.Request, aiohttp_web.Application]


def create_client() -> Client:
    app = app_http_server.HttpServerAppFactory(settings=app_settings.Settings()).create()
    return aiohttp_test_utils.TestClient(aiohttp_test_utils.TestServer(app))


@pytest.mark.asyncio
async def test_liveness_probe():
    async with create_client() as client:
        response = await client.get("/health/liveness")

        assert response.status == 200
        assert await response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_app_info(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP__NAME", "test-service")
    monkeypatch.setenv("APP__VERSION", "1.2.3")

    async with create_client() as client:
        response = await client.get("/api/v1/info")

        assert response.status == 200
        assert await response.json() == {"name": "test-service", "version": "1.2.3"}
