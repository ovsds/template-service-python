import collections.abc
import dataclasses
import html
import http
import logging
import posixpath
import re
import types
import typing

import aiohttp.hdrs as aiohttp_hdrs
import aiohttp.web as aiohttp_web
import pydantic
import pydantic.json_schema as pydantic_json_schema

import lib.utils.aiohttp.handlers.base as handlers_base
import lib.utils.aiohttp.handlers.responses as aiohttp_responses
import lib.utils.json as json_utils
import lib.utils.pydantic as pydantic_utils

OPENAPI_VERSION = "3.1.0"
SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.33.3"
SWAGGER_UI_CSS_INTEGRITY = "sha384-Ov4/wv3j2bmct8cDc5X4ngJZohVPzEmc6uDPH8WeljUxO5vtoykvMEfbu9Vh6RaW"
SWAGGER_UI_BUNDLE_INTEGRITY = "sha384-h00llMzD1afyNow1pDmnZKlHsUZgp9KE9HXLFXF2CvbwsBY0+WBO4f75SfGwvM4K"

logger = logging.getLogger(__name__)

_SCHEMA_REF_PREFIX = "#/components/schemas/"
# aiohttp path variables may carry a regex, "{name:\d+}"; OpenAPI paths take the bare "{name}"
_PATH_VARIABLE_REGEX = re.compile(r"\{(?P<name>[^{}:]+):[^{}]*(?:\{[^{}]*\}[^{}]*)*\}")
_BARE_PATH_VARIABLE_REGEX = re.compile(r"\{(?P<name>[^{}]+)\}")

_ModelKey = tuple[type[pydantic.BaseModel], pydantic_json_schema.JsonSchemaMode]


class ErrorResponse(pydantic_utils.BaseModel):
    code: str
    message: str


@dataclasses.dataclass(frozen=True)
class OpenApiInfo:
    title: str
    version: str
    description: str = ""


@dataclasses.dataclass(frozen=True)
class _Operation:
    route: handlers_base.Route
    path_model: type[pydantic.BaseModel] | None = None
    query_model: type[pydantic.BaseModel] | None = None
    body_model: type[pydantic.BaseModel] | None = None
    body_required: bool = False
    response_model: type[pydantic.BaseModel] | None = None
    has_request_schema: bool = False

    @classmethod
    def from_route(cls, route: handlers_base.Route) -> typing.Self:
        handler_class = type(route.handler)
        response_model = getattr(handler_class, "ResponseSchema", None)
        if not (isinstance(response_model, type) and issubclass(response_model, handlers_base.BaseResponseSchema)):
            response_model = None

        request_schema = getattr(handler_class, "RequestSchema", None)
        if not (isinstance(request_schema, type) and issubclass(request_schema, handlers_base.BaseRequestSchema)):
            return cls(route=route, response_model=response_model)

        body_field = request_schema.model_fields.get("body")
        body_model = cls._get_field_model(request_schema, "body")
        return cls(
            route=route,
            path_model=cls._get_field_model(request_schema, "path"),
            query_model=cls._get_field_model(request_schema, "query"),
            body_model=body_model,
            # A request without a body validates "{}", which needs no body when every body field has a default
            body_required=(
                body_field is not None
                and body_field.is_required()
                and body_model is not None
                and any(field.is_required() for field in body_model.model_fields.values())
            ),
            response_model=response_model,
            has_request_schema=True,
        )

    @staticmethod
    def _get_field_model(
        request_schema: type[handlers_base.BaseRequestSchema],
        field_name: str,
    ) -> type[pydantic.BaseModel] | None:
        field = request_schema.model_fields.get(field_name)
        if field is None:
            return None
        # pydantic strips Annotated from field annotations; "Model | None" is unwrapped to Model
        candidates = [arg for arg in typing.get_args(field.annotation) if arg is not types.NoneType]
        if len(candidates) != 1:
            candidates = [field.annotation]
        model = candidates[0]
        if isinstance(model, type) and issubclass(model, pydantic.BaseModel):
            return model
        # The spec leaves the field out rather than fail the app that serves it
        logger.warning("OpenAPI skips %s.%s: not a pydantic model", request_schema.__qualname__, field_name)
        return None

    @property
    def model_keys(self) -> list[_ModelKey]:
        keys: list[_ModelKey] = [
            (model, "validation") for model in (self.path_model, self.query_model, self.body_model) if model is not None
        ]
        if self.response_model is not None:
            keys.append((self.response_model, "serialization"))
        if self.has_request_schema:
            keys.append((ErrorResponse, "serialization"))
        return keys


@dataclasses.dataclass(frozen=True)
class _SpecBuilder:
    refs: typing.Mapping[_ModelKey, typing.Any]
    schemas: typing.Mapping[str, typing.Any]

    @classmethod
    def from_operations(cls, operations: collections.abc.Sequence[_Operation]) -> typing.Self:
        # One pass over every model, so pydantic gives same-named models of different handlers distinct names
        model_keys = list(dict.fromkeys(key for operation in operations for key in operation.model_keys))
        refs, definitions = pydantic_json_schema.models_json_schema(
            model_keys,
            ref_template=_SCHEMA_REF_PREFIX + "{model}",
        )
        return cls(refs={key: refs[key] for key in model_keys}, schemas=definitions.get("$defs", {}))

    def build_operation(self, operation: _Operation, path: str) -> dict[str, typing.Any]:
        result: dict[str, typing.Any] = {}
        if operation.route.openapi_tags:
            result["tags"] = list(operation.route.openapi_tags)
        if operation.route.openapi_summary:
            result["summary"] = operation.route.openapi_summary

        path_parameters = self._build_parameters(operation.path_model, "path")
        documented = {parameter["name"] for parameter in path_parameters}
        # OpenAPI needs every path template variable declared, also one the handler reads without a path model
        path_parameters.extend(
            {"name": name, "in": "path", "required": True, "schema": {"type": "string"}}
            for name in _BARE_PATH_VARIABLE_REGEX.findall(path)
            if name not in documented
        )
        parameters = [*path_parameters, *self._build_parameters(operation.query_model, "query")]
        if parameters:
            result["parameters"] = parameters

        if operation.body_model is not None:
            result["requestBody"] = {
                "required": operation.body_required,
                "content": {"application/json": {"schema": self.refs[(operation.body_model, "validation")]}},
            }

        responses = {str(http.HTTPStatus.OK.value): self._build_response(http.HTTPStatus.OK, operation.response_model)}
        if operation.has_request_schema:
            responses[str(http.HTTPStatus.BAD_REQUEST.value)] = self._build_response(
                http.HTTPStatus.BAD_REQUEST,
                ErrorResponse,
            )
        result["responses"] = responses
        return result

    def _build_parameters(
        self,
        model: type[pydantic.BaseModel] | None,
        location: typing.Literal["path", "query"],
    ) -> list[dict[str, typing.Any]]:
        if model is None:
            return []
        schema = self._resolve(self.refs[(model, "validation")])
        required: collections.abc.Collection[str] = schema.get("required", [])
        return [
            {
                "name": name,
                "in": location,
                "required": location == "path" or name in required,
                "schema": property_schema,
            }
            for name, property_schema in schema.get("properties", {}).items()
        ]

    def _build_response(self, status: http.HTTPStatus, model: type[pydantic.BaseModel] | None) -> dict[str, typing.Any]:
        response: dict[str, typing.Any] = {"description": status.phrase}
        if model is not None:
            response["content"] = {"application/json": {"schema": self.refs[(model, "serialization")]}}
        return response

    def _resolve(self, schema: typing.Mapping[str, typing.Any]) -> typing.Mapping[str, typing.Any]:
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith(_SCHEMA_REF_PREFIX):
            return self.schemas[ref.removeprefix(_SCHEMA_REF_PREFIX)]
        return schema


def build_openapi_spec(
    info: OpenApiInfo,
    routes: collections.abc.Sequence[handlers_base.Route],
) -> dict[str, typing.Any]:
    operations = [
        _Operation.from_route(route)
        for route in routes
        if route.openapi_include and route.method != aiohttp_hdrs.METH_ANY
    ]
    builder = _SpecBuilder.from_operations(operations)

    paths: dict[str, dict[str, typing.Any]] = {}
    for operation in operations:
        path = _PATH_VARIABLE_REGEX.sub(r"{\g<name>}", operation.route.path)
        paths.setdefault(path, {})[operation.route.method.lower()] = builder.build_operation(operation, path)

    info_data = {"title": info.title, "version": info.version}
    if info.description:
        info_data["description"] = info.description

    spec: dict[str, typing.Any] = {"openapi": OPENAPI_VERSION, "info": info_data, "paths": paths}
    if builder.schemas:
        spec["components"] = {"schemas": dict(builder.schemas)}
    return spec


@dataclasses.dataclass(frozen=True)
class OpenApiSpecHandler(handlers_base.BaseHandler):
    spec: typing.Mapping[str, typing.Any]

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        return aiohttp_responses.Response.with_data(data=self.spec)


@dataclasses.dataclass(frozen=True)
class SwaggerUIHandler(handlers_base.BaseHandler):
    title: str
    spec_url: str

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        return aiohttp_responses.Response.with_text(text=self.render(), content_type="text/html")

    def render(self) -> str:
        title = html.escape(self.title)
        # The config lands in a script: JSON keeps its values literals, an escaped "<" keeps "</script>" out
        config = json_utils.dumps_str({"url": self.spec_url, "dom_id": "#swagger-ui", "deepLinking": True})
        config = config.replace("<", "\\u003c")
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <link
      rel="stylesheet"
      href="{SWAGGER_UI_URL}/swagger-ui.css"
      integrity="{SWAGGER_UI_CSS_INTEGRITY}"
      crossorigin="anonymous"
    />
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script
      src="{SWAGGER_UI_URL}/swagger-ui-bundle.js"
      integrity="{SWAGGER_UI_BUNDLE_INTEGRITY}"
      crossorigin="anonymous"
    ></script>
    <script>
      window.ui = SwaggerUIBundle({config});
    </script>
  </body>
</html>
"""


def create_openapi_routes(
    info: OpenApiInfo,
    routes: collections.abc.Sequence[handlers_base.Route],
    docs_path: str,
) -> list[handlers_base.Route]:
    docs_path = docs_path.rstrip("/")
    spec_path = f"{docs_path}/spec.json"
    # Relative to the docs page, so the UI keeps working behind a proxy that adds a path prefix
    spec_url = posixpath.relpath(spec_path, posixpath.dirname(docs_path))
    return [
        handlers_base.Route(
            method="GET",
            path=spec_path,
            handler=OpenApiSpecHandler(spec=build_openapi_spec(info=info, routes=routes)),
            openapi_include=False,
        ),
        handlers_base.Route(
            method="GET",
            path=docs_path,
            handler=SwaggerUIHandler(title=info.title, spec_url=spec_url),
            openapi_include=False,
        ),
    ]


__all__ = [
    "OpenApiInfo",
    "OpenApiSpecHandler",
    "SwaggerUIHandler",
    "build_openapi_spec",
    "create_openapi_routes",
]
