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
class StreamingHandler(aiohttp_utils.BaseHandler):
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        response = aiohttp_web.StreamResponse()
        await response.prepare(request)
        await response.write(b"ok")
        await response.write_eof()
        return response


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
            aiohttp_utils.Route(method="GET", path="/stream", handler=StreamingHandler()),
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


@pytest.mark.asyncio
async def test_request_id_is_taken_from_header():
    async with create_client() as client:
        response = await client.get("/log", headers={aiohttp_utils.REQUEST_ID_HEADER: "test-request.id_1"})

        assert response.status == 200
        assert response.headers[aiohttp_utils.REQUEST_ID_HEADER] == "test-request.id_1"


@pytest.mark.asyncio
async def test_request_id_is_generated_when_header_is_absent():
    async with create_client() as client:
        first_response = await client.get("/log")
        second_response = await client.get("/log")

        first_request_id = first_response.headers[aiohttp_utils.REQUEST_ID_HEADER]
        assert len(first_request_id) == 32
        assert first_request_id != second_response.headers[aiohttp_utils.REQUEST_ID_HEADER]


@pytest.mark.parametrize(
    "request_id",
    [
        "",
        "a" * 129,
        "forged | status=200 | line",
    ],
)
@pytest.mark.asyncio
async def test_request_id_is_generated_when_header_is_invalid(request_id: str):
    async with create_client() as client:
        response = await client.get("/log", headers={aiohttp_utils.REQUEST_ID_HEADER: request_id})

        response_request_id = response.headers[aiohttp_utils.REQUEST_ID_HEADER]
        assert response_request_id != request_id
        assert len(response_request_id) == 32


@pytest.mark.asyncio
async def test_request_id_is_accepted_at_max_length():
    request_id = "a" * 128
    async with create_client() as client:
        response = await client.get("/log", headers={aiohttp_utils.REQUEST_ID_HEADER: request_id})

        assert response.headers[aiohttp_utils.REQUEST_ID_HEADER] == request_id


@pytest.mark.asyncio
async def test_request_id_is_returned_on_streamed_response():
    async with create_client() as client:
        response = await client.get("/stream", headers={aiohttp_utils.REQUEST_ID_HEADER: "stream-request-id"})

        assert response.status == 200
        assert await response.read() == b"ok"
        assert response.headers[aiohttp_utils.REQUEST_ID_HEADER] == "stream-request-id"


@pytest.mark.asyncio
async def test_request_id_is_returned_on_error_responses():
    async with create_client() as client:
        internal_error_response = await client.get(
            "/error",
            headers={aiohttp_utils.REQUEST_ID_HEADER: "error-request-id"},
        )
        not_found_response = await client.get(
            "/unknown",
            headers={aiohttp_utils.REQUEST_ID_HEADER: "unknown-request-id"},
        )
        redirect_response = await client.get(
            "/redirect",
            headers={aiohttp_utils.REQUEST_ID_HEADER: "redirect-request-id"},
            allow_redirects=False,
        )

        assert internal_error_response.status == 500
        assert internal_error_response.headers[aiohttp_utils.REQUEST_ID_HEADER] == "error-request-id"
        assert not_found_response.status == 404
        assert not_found_response.headers[aiohttp_utils.REQUEST_ID_HEADER] == "unknown-request-id"
        assert redirect_response.status == 302
        assert redirect_response.headers[aiohttp_utils.REQUEST_ID_HEADER] == "redirect-request-id"


@pytest.mark.asyncio
async def test_log_records_carry_request_id(request_logs: pytest.LogCaptureFixture):
    request_logs.set_level(logging.INFO)
    async with create_client() as client:
        await client.get("/log", headers={aiohttp_utils.REQUEST_ID_HEADER: "test-request-id"})
        await client.get("/error", headers={aiohttp_utils.REQUEST_ID_HEADER: "error-request-id"})

        handler_records = [record for record in request_logs.records if record.getMessage() == "Handling request"]
        assert len(handler_records) == 1
        assert get_record_request_id(handler_records[0]) == "test-request-id"
        error_records = [record for record in request_logs.records if record.exc_info is not None]
        assert len(error_records) == 1
        assert get_record_request_id(error_records[0]) == "error-request-id"


def test_log_records_outside_request_have_placeholder_request_id(request_logs: pytest.LogCaptureFixture):
    request_logs.set_level(logging.INFO)
    logger.info("Outside request")

    records = [record for record in request_logs.records if record.getMessage() == "Outside request"]
    assert len(records) == 1
    assert get_record_request_id(records[0]) == "-"
