import dataclasses
import typing

import aiohttp.test_utils as aiohttp_test_utils
import aiohttp.web as aiohttp_web
import pydantic
import pytest

import lib.utils.aiohttp as aiohttp_utils
import lib.utils.pydantic as pydantic_utils

INFO = aiohttp_utils.OpenApiInfo(title="Example", version="1.0.0")


class Color(pydantic_utils.BaseModel):
    name: str


class CreateItemRequestPathSchema(pydantic_utils.BaseModel):
    shop_id: int


class CreateItemRequestQuerySchema(pydantic_utils.BaseModel):
    dry_run: bool = False
    tag: list[str] = pydantic.Field(default_factory=list)
    token: str


class CreateItemRequestBodySchema(pydantic_utils.BaseModel):
    name: str
    color: Color


@dataclasses.dataclass(frozen=True)
class CreateItemHandler(aiohttp_utils.BaseHandler):
    class RequestSchema(aiohttp_utils.BaseRequestSchema):
        path: CreateItemRequestPathSchema
        query: CreateItemRequestQuerySchema
        body: CreateItemRequestBodySchema

    class ResponseSchema(aiohttp_utils.BaseResponseSchema):
        item_id: int
        color: Color

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class OtherHandler(aiohttp_utils.BaseHandler):
    class ResponseSchema(aiohttp_utils.BaseResponseSchema):
        other: str

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class PlainHandler(aiohttp_utils.BaseHandler):
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise NotImplementedError


class InvalidRequestSchema(aiohttp_utils.BaseRequestSchema):
    query: dict[str, str]


@dataclasses.dataclass(frozen=True)
class InvalidRequestHandler(aiohttp_utils.BaseHandler):
    RequestSchema = InvalidRequestSchema

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise NotImplementedError


def build_spec(routes: list[aiohttp_utils.Route]) -> dict[str, typing.Any]:
    return aiohttp_utils.build_openapi_spec(info=INFO, routes=routes)


def resolve(spec: dict[str, typing.Any], schema: dict[str, typing.Any]) -> dict[str, typing.Any]:
    return spec["components"]["schemas"][schema["$ref"].removeprefix("#/components/schemas/")]


def test_spec_documents_handler_schemas():
    spec = build_spec(
        [
            aiohttp_utils.Route(
                method="POST",
                path=r"/shops/{shop_id:\d+}/items",
                handler=CreateItemHandler(),
                openapi_tags=["items"],
                openapi_summary="Create an item",
            ),
        ]
    )

    assert spec["openapi"] == "3.1.0"
    assert spec["info"] == {"title": "Example", "version": "1.0.0"}
    operation = spec["paths"]["/shops/{shop_id}/items"]["post"]
    assert operation["tags"] == ["items"]
    assert operation["summary"] == "Create an item"
    assert [(parameter["name"], parameter["in"], parameter["required"]) for parameter in operation["parameters"]] == [
        ("shop_id", "path", True),
        ("dry_run", "query", False),
        ("tag", "query", False),
        ("token", "query", True),
    ]
    assert operation["parameters"][2]["schema"]["type"] == "array"

    request_body = operation["requestBody"]
    assert request_body["required"] is True
    body_schema = resolve(spec, request_body["content"]["application/json"]["schema"])
    assert set(body_schema["properties"]) == {"name", "color"}
    assert resolve(spec, body_schema["properties"]["color"]) == spec["components"]["schemas"]["Color"]

    response_schema = resolve(spec, operation["responses"]["200"]["content"]["application/json"]["schema"])
    assert set(response_schema["properties"]) == {"item_id", "color"}
    assert operation["responses"]["200"]["description"] == "OK"

    error_schema = resolve(spec, operation["responses"]["400"]["content"]["application/json"]["schema"])
    assert set(error_schema["properties"]) == {"code", "message"}


def test_spec_names_same_named_schemas_apart():
    spec = build_spec(
        [
            aiohttp_utils.Route(method="POST", path="/items", handler=CreateItemHandler()),
            aiohttp_utils.Route(method="GET", path="/other", handler=OtherHandler()),
        ]
    )

    item_ref = spec["paths"]["/items"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    other_ref = spec["paths"]["/other"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert item_ref != other_ref
    assert set(resolve(spec, item_ref)["properties"]) == {"item_id", "color"}
    assert set(resolve(spec, other_ref)["properties"]) == {"other"}


def test_spec_documents_handler_without_schemas():
    spec = build_spec([aiohttp_utils.Route(method="GET", path="/plain", handler=PlainHandler())])

    assert spec["paths"] == {"/plain": {"get": {"responses": {"200": {"description": "OK"}}}}}
    assert "components" not in spec


def test_spec_skips_excluded_and_wildcard_routes():
    spec = build_spec(
        [
            aiohttp_utils.Route(method="GET", path="/hidden", handler=PlainHandler(), openapi_include=False),
            aiohttp_utils.Route(method="*", path="/any", handler=PlainHandler()),
        ]
    )

    assert spec["paths"] == {}


def test_spec_skips_request_field_that_is_not_a_model():
    spec = build_spec([aiohttp_utils.Route(method="GET", path="/invalid", handler=InvalidRequestHandler())])

    assert "parameters" not in spec["paths"]["/invalid"]["get"]


class OptionalBodyRequestBodySchema(pydantic_utils.BaseModel):
    note: str = ""


@dataclasses.dataclass(frozen=True)
class OptionalBodyHandler(aiohttp_utils.BaseHandler):
    class RequestSchema(aiohttp_utils.BaseRequestSchema):
        body: OptionalBodyRequestBodySchema | None = None

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class DefaultsBodyHandler(aiohttp_utils.BaseHandler):
    class RequestSchema(aiohttp_utils.BaseRequestSchema):
        body: OptionalBodyRequestBodySchema

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        raise NotImplementedError


@pytest.mark.parametrize("handler", [OptionalBodyHandler(), DefaultsBodyHandler()])
def test_spec_documents_body_that_may_be_left_out(handler: aiohttp_utils.BaseHandler):
    spec = build_spec([aiohttp_utils.Route(method="POST", path="/notes", handler=handler)])

    request_body = spec["paths"]["/notes"]["post"]["requestBody"]
    assert request_body["required"] is False
    assert set(resolve(spec, request_body["content"]["application/json"]["schema"])["properties"]) == {"note"}


def test_spec_declares_path_variables_without_path_model():
    spec = build_spec([aiohttp_utils.Route(method="GET", path=r"/plain/{plain_id:\d+}", handler=PlainHandler())])

    assert spec["paths"]["/plain/{plain_id}"]["get"]["parameters"] == [
        {"name": "plain_id", "in": "path", "required": True, "schema": {"type": "string"}},
    ]


@dataclasses.dataclass(frozen=True)
class ExampleAppFactory(aiohttp_utils.AppFactory):
    def get_routes(self) -> list[aiohttp_utils.Route]:
        return [aiohttp_utils.Route(method="POST", path="/items", handler=CreateItemHandler())]

    def get_openapi_info(self) -> aiohttp_utils.OpenApiInfo:
        return aiohttp_utils.OpenApiInfo(title="Example </script>", version="1.0.0")

    def get_openapi_docs_path(self) -> str:
        return "/docs"


Client = aiohttp_test_utils.TestClient[aiohttp_web.Request, aiohttp_web.Application]


def create_client(app_factory: aiohttp_utils.AppFactory) -> Client:
    return aiohttp_test_utils.TestClient(aiohttp_test_utils.TestServer(app_factory.create()))


@pytest.mark.asyncio
async def test_app_serves_spec():
    async with create_client(ExampleAppFactory()) as client:
        response = await client.get("/docs/spec.json")

        assert response.status == 200
        spec = await response.json()
        assert list(spec["paths"]) == ["/items"]


@pytest.mark.asyncio
async def test_app_serves_swagger_ui():
    async with create_client(ExampleAppFactory()) as client:
        response = await client.get("/docs")

        assert response.status == 200
        assert response.content_type == "text/html"
        page = await response.text()
        assert '"url":"docs/spec.json"' in page
        assert "<title>Example &lt;/script&gt;</title>" in page
        assert 'integrity="sha384-' in page


@dataclasses.dataclass(frozen=True)
class TrailingSlashAppFactory(ExampleAppFactory):
    def get_openapi_docs_path(self) -> str:
        return "/docs/"


@pytest.mark.asyncio
async def test_app_serves_docs_path_with_trailing_slash():
    async with create_client(TrailingSlashAppFactory()) as client:
        assert (await client.get("/docs")).status == 200
        assert (await client.get("/docs/spec.json")).status == 200


@pytest.mark.asyncio
async def test_app_without_openapi_info_serves_no_docs():
    async with create_client(aiohttp_utils.AppFactory()) as client:
        response = await client.get("/api/v1/docs/spec.json")

        assert response.status == 404
