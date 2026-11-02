import asyncio
import dataclasses
import logging

import aiohttp.test_utils as aiohttp_test_utils
import aiohttp.web as aiohttp_web
import pytest

import lib.utils.aiohttp as aiohttp_utils


@dataclasses.dataclass(frozen=True)
class OkHandler(aiohttp_utils.BaseHandler):
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        return aiohttp_web.Response(text="ok")


@dataclasses.dataclass(frozen=True)
class RaisingHandler(aiohttp_utils.BaseHandler):
    exception: Exception

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise self.exception


@dataclasses.dataclass(frozen=True)
class ExampleAppFactory(aiohttp_utils.AppFactory):
    def get_routes(self) -> list[aiohttp_utils.Route]:
        return [
            aiohttp_utils.Route(method="GET", path="/ok", handler=OkHandler()),
            aiohttp_utils.Route(method="GET", path="/error", handler=RaisingHandler(exception=RuntimeError("boom"))),
            aiohttp_utils.Route(
                method="GET",
                path="/redirect",
                handler=RaisingHandler(exception=aiohttp_web.HTTPFound(location="/ok")),
            ),
        ]


Client = aiohttp_test_utils.TestClient[aiohttp_web.Request, aiohttp_web.Application]


def create_client() -> Client:
    app = ExampleAppFactory().create()
    return aiohttp_test_utils.TestClient(aiohttp_test_utils.TestServer(app))


@pytest.fixture
def request_logs(caplog: pytest.LogCaptureFixture):
    # pytest resets the capture level to log_level when the test call starts, so tests set INFO themselves
    log_filter = aiohttp_utils.RequestContextLogFilter()
    caplog.handler.addFilter(log_filter)
    yield caplog
    caplog.handler.removeFilter(log_filter)


def get_request_log_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == aiohttp_utils.RequestLoggingMiddleware.__module__]


@pytest.mark.asyncio
async def test_request_is_logged_once(request_logs: pytest.LogCaptureFixture):
    request_logs.set_level(logging.INFO)
    async with create_client() as client:
        await client.get("/ok", params={"query": "value"}, headers={aiohttp_utils.REQUEST_ID_HEADER: "test-request-id"})

        records = get_request_log_records(request_logs)
        assert len(records) == 1
        assert records[0].__dict__.get("request_id") == "test-request-id"
        assert "method=GET path=/ok status=200 duration_ms=" in records[0].getMessage()


@pytest.mark.asyncio
async def test_failed_request_is_logged_with_error_response_status(request_logs: pytest.LogCaptureFixture):
    request_logs.set_level(logging.INFO)
    async with create_client() as client:
        await client.get("/error")
        await client.get("/redirect", allow_redirects=False)

        messages = [record.getMessage() for record in get_request_log_records(request_logs)]
        assert len(messages) == 2
        assert "method=GET path=/error status=500" in messages[0]
        assert "method=GET path=/redirect status=302" in messages[1]


@pytest.mark.asyncio
async def test_cancelled_request_is_logged_as_cancelled(request_logs: pytest.LogCaptureFixture):
    request_logs.set_level(logging.INFO)
    middleware = aiohttp_utils.RequestLoggingMiddleware()
    request = aiohttp_test_utils.make_mocked_request("GET", "/slow")

    async def handler(request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await middleware.process(request, handler)

    messages = [record.getMessage() for record in get_request_log_records(request_logs)]
    assert len(messages) == 1
    assert "method=GET path=/slow status=cancelled" in messages[0]
