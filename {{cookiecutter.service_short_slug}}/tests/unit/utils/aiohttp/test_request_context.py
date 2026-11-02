import dataclasses
import logging

import aiohttp.test_utils as aiohttp_test_utils
import aiohttp.web as aiohttp_web
import pytest

import lib.utils.aiohttp as aiohttp_utils

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class LoggingHandler(aiohttp_utils.BaseHandler):
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        logger.info("Handling request")
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
            aiohttp_utils.Route(method="GET", path="/log", handler=LoggingHandler()),
            aiohttp_utils.Route(method="GET", path="/error", handler=RaisingHandler(exception=RuntimeError("boom"))),
            aiohttp_utils.Route(
                method="GET",
                path="/redirect",
                handler=RaisingHandler(exception=aiohttp_web.HTTPFound(location="/log")),
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


def get_record_request_id(record: logging.LogRecord) -> str | None:
    # The filter sets an attribute LogRecord does not declare
    return record.__dict__.get("request_id")


def get_request_log_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == aiohttp_utils.RequestLoggingMiddleware.__module__]


@pytest.mark.asyncio
async def test_request_id_is_taken_from_header():
    async with create_client() as client:
        response = await client.get("/log", headers={"X-Request-ID": "test-request-id"})

        assert response.status == 200
        assert response.headers["X-Request-ID"] == "test-request-id"


@pytest.mark.asyncio
async def test_request_id_is_generated_when_header_is_absent():
    async with create_client() as client:
        first_response = await client.get("/log")
        second_response = await client.get("/log")

        first_request_id = first_response.headers["X-Request-ID"]
        assert len(first_request_id) == 32
        assert first_request_id != second_response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_request_id_is_returned_on_error_responses():
    async with create_client() as client:
        internal_error_response = await client.get("/error", headers={"X-Request-ID": "error-request-id"})
        not_found_response = await client.get("/unknown", headers={"X-Request-ID": "unknown-request-id"})
        redirect_response = await client.get(
            "/redirect",
            headers={"X-Request-ID": "redirect-request-id"},
            allow_redirects=False,
        )

        assert internal_error_response.status == 500
        assert internal_error_response.headers["X-Request-ID"] == "error-request-id"
        assert not_found_response.status == 404
        assert not_found_response.headers["X-Request-ID"] == "unknown-request-id"
        assert redirect_response.status == 302
        assert redirect_response.headers["X-Request-ID"] == "redirect-request-id"


@pytest.mark.asyncio
async def test_log_records_carry_request_id(request_logs: pytest.LogCaptureFixture):
    request_logs.set_level(logging.INFO)
    async with create_client() as client:
        await client.get("/log", headers={"X-Request-ID": "test-request-id"})

        records = [record for record in request_logs.records if record.getMessage() == "Handling request"]
        assert len(records) == 1
        assert get_record_request_id(records[0]) == "test-request-id"


def test_log_records_outside_request_have_placeholder_request_id(request_logs: pytest.LogCaptureFixture):
    request_logs.set_level(logging.INFO)
    logger.info("Outside request")

    records = [record for record in request_logs.records if record.getMessage() == "Outside request"]
    assert len(records) == 1
    assert get_record_request_id(records[0]) == "-"


@pytest.mark.asyncio
async def test_request_is_logged_once(request_logs: pytest.LogCaptureFixture):
    request_logs.set_level(logging.INFO)
    async with create_client() as client:
        await client.get("/log", params={"query": "value"}, headers={"X-Request-ID": "test-request-id"})

        records = get_request_log_records(request_logs)
        assert len(records) == 1
        assert get_record_request_id(records[0]) == "test-request-id"
        message = records[0].getMessage()
        assert "method=GET path=/log status=200 duration_ms=" in message


@pytest.mark.asyncio
async def test_failed_request_is_logged_with_error_response_status(request_logs: pytest.LogCaptureFixture):
    request_logs.set_level(logging.INFO)
    async with create_client() as client:
        await client.get("/error", headers={"X-Request-ID": "error-request-id"})
        await client.get("/redirect", allow_redirects=False)

        messages = [record.getMessage() for record in get_request_log_records(request_logs)]
        assert len(messages) == 2
        assert "method=GET path=/error status=500" in messages[0]
        assert "method=GET path=/redirect status=302" in messages[1]
        error_records = [record for record in request_logs.records if record.exc_info is not None]
        assert len(error_records) == 1
        assert get_record_request_id(error_records[0]) == "error-request-id"
