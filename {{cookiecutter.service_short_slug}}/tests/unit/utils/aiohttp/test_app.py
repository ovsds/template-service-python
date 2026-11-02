import dataclasses
import typing

import aiohttp.test_utils as aiohttp_test_utils
import aiohttp.web as aiohttp_web
import pytest

import lib.utils.aiohttp as aiohttp_utils
import lib.utils.pydantic as pydantic_utils


class ItemNotFoundError(Exception): ...


class ItemNotFoundResponseSchema(aiohttp_utils.ErrorResponseSchema):
    code: str = "ITEM_NOT_FOUND"
    message: str = "Item not found"
    status_code: int = 404


class EchoRequestBodySchema(pydantic_utils.BaseModel):
    name: str


class EchoRequestQuerySchema(pydantic_utils.BaseModel):
    limit: int = 10


@dataclasses.dataclass(frozen=True)
class EchoHandler(aiohttp_utils.BaseHandler):
    class RequestSchema(aiohttp_utils.BaseRequestSchema):
        body: EchoRequestBodySchema
        query: EchoRequestQuerySchema

    class ResponseSchema(aiohttp_utils.BaseResponseSchema):
        name: str
        limit: int

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        request_schema = await self.RequestSchema.from_request(request)
        response_schema = self.ResponseSchema(name=request_schema.body.name, limit=request_schema.query.limit)
        return response_schema.as_response(status=201)


@dataclasses.dataclass(frozen=True)
class RaisingHandler(aiohttp_utils.BaseHandler):
    exception: Exception

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise self.exception


@dataclasses.dataclass(frozen=True)
class ExampleAppFactory(aiohttp_utils.AppFactory):
    def get_routes(self) -> list[aiohttp_utils.Route]:
        return [
            aiohttp_utils.Route(method="POST", path="/echo", handler=EchoHandler()),
            aiohttp_utils.Route(method="GET", path="/item", handler=RaisingHandler(exception=ItemNotFoundError())),
            aiohttp_utils.Route(method="GET", path="/error", handler=RaisingHandler(exception=RuntimeError("boom"))),
            aiohttp_utils.Route(
                method="GET",
                path="/redirect",
                handler=RaisingHandler(exception=aiohttp_web.HTTPFound(location="/echo")),
            ),
        ]

    def get_error_map(self) -> typing.Mapping[type[Exception], aiohttp_utils.ErrorResponseSchema]:
        return {
            **super().get_error_map(),
            ItemNotFoundError: ItemNotFoundResponseSchema(),
        }


Client = aiohttp_test_utils.TestClient[aiohttp_web.Request, aiohttp_web.Application]


def create_client() -> Client:
    app = ExampleAppFactory().create()
    return aiohttp_test_utils.TestClient(aiohttp_test_utils.TestServer(app))


@pytest.mark.asyncio
async def test_handler_parses_request_and_serialises_response():
    async with create_client() as client:
        response = await client.post("/echo", params={"limit": "5"}, json={"name": "test"})

        assert response.status == 201
        assert await response.json() == {"name": "test", "limit": 5}


@pytest.mark.asyncio
async def test_handler_responds_bad_request_on_invalid_body():
    async with create_client() as client:
        response = await client.post("/echo", json={"title": "test"})

        assert response.status == 400
        assert await response.json() == {"code": "BAD_REQUEST", "message": "Bad request"}


@pytest.mark.asyncio
async def test_handler_responds_bad_request_on_malformed_json():
    async with create_client() as client:
        response = await client.post("/echo", data=b"{", headers={"Content-Type": "application/json"})

        assert response.status == 400
        assert await response.json() == {"code": "BAD_REQUEST", "message": "Bad request"}


@pytest.mark.asyncio
async def test_error_middleware_maps_exception():
    async with create_client() as client:
        response = await client.get("/item")

        assert response.status == 404
        assert await response.json() == {"code": "ITEM_NOT_FOUND", "message": "Item not found"}


@pytest.mark.asyncio
async def test_error_middleware_maps_unknown_route():
    async with create_client() as client:
        response = await client.get("/unknown")

        assert response.status == 404
        assert await response.json() == {"code": "NOT_FOUND", "message": "Not found"}


@pytest.mark.asyncio
async def test_error_middleware_maps_wrong_method():
    async with create_client() as client:
        response = await client.get("/echo")

        assert response.status == 405
        assert await response.json() == {"code": "METHOD_NOT_ALLOWED", "message": "Method not allowed"}


@pytest.mark.asyncio
async def test_error_middleware_passes_unmapped_http_exception():
    async with create_client() as client:
        response = await client.get("/redirect", allow_redirects=False)

        assert response.status == 302
        assert response.headers["Location"] == "/echo"


@pytest.mark.asyncio
async def test_error_middleware_falls_back_to_internal_server_error(caplog: pytest.LogCaptureFixture):
    async with create_client() as client:
        response = await client.get("/error")

        assert response.status == 500
        assert await response.json() == {"code": "INTERNAL_SERVER_ERROR", "message": "Internal server error"}
        assert any(
            record.exc_info is not None and isinstance(record.exc_info[1], RuntimeError) for record in caplog.records
        )
