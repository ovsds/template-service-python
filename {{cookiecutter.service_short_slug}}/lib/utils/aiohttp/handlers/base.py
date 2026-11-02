import abc
import collections.abc
import dataclasses
import http
import types
import typing

import aiohttp.web as aiohttp_web
import pydantic

import lib.utils.aiohttp.handlers.responses as aiohttp_responses
import lib.utils.json as json_utils
import lib.utils.pydantic as pydantic_utils

_SEQUENCE_ORIGINS = (list, tuple, set, frozenset, collections.abc.Sequence)


def _accepts_sequence(annotation: typing.Any) -> bool:
    origin = typing.get_origin(annotation)
    if origin in _SEQUENCE_ORIGINS:
        return True
    if origin in (typing.Union, types.UnionType):
        return any(_accepts_sequence(arg) for arg in typing.get_args(annotation))
    return False


class RequestValidationError(Exception): ...


class BaseRequestSchema(pydantic_utils.BaseModel):
    @classmethod
    async def from_request(cls, request: aiohttp_web.Request) -> typing.Self:
        try:
            data: dict[str, typing.Any] = {
                "path": dict(request.match_info),
                "query": cls._get_query(request),
            }
            if "body" in cls.model_fields:
                data["body"] = json_utils.loads_bytes(await request.read()) if request.body_exists else {}
            return cls.model_validate(data)
        except ValueError as exc:
            raise RequestValidationError("Failed to parse request") from exc

    @classmethod
    def _get_query(cls, request: aiohttp_web.Request) -> dict[str, str | list[str]]:
        sequence_keys: set[str] = set()
        query_field = cls.model_fields.get("query")
        if query_field is not None:
            query_schema = query_field.annotation
            if isinstance(query_schema, type) and issubclass(query_schema, pydantic.BaseModel):
                sequence_keys = {
                    field.alias or name
                    for name, field in query_schema.model_fields.items()
                    if _accepts_sequence(field.annotation)
                }

        return {key: request.query.getall(key) if key in sequence_keys else request.query[key] for key in request.query}


class BaseResponseSchema(pydantic_utils.BaseModel):
    def as_data(self) -> typing.Any:
        return self.model_dump(mode="json")

    def as_response(
        self,
        status: int = http.HTTPStatus.OK,
        headers: typing.Mapping[str, str] | None = None,
    ) -> aiohttp_responses.Response:
        return aiohttp_responses.Response.with_data(data=self.as_data(), status=status, headers=headers)


class ErrorResponseSchema(BaseResponseSchema):
    code: str
    message: str
    status_code: int

    def as_data(self) -> typing.Any:
        return self.model_dump(mode="json", exclude={"status_code"})

    def as_error_response(self, headers: typing.Mapping[str, str] | None = None) -> aiohttp_responses.Response:
        return self.as_response(status=self.status_code, headers=headers)


class BaseHandler(typing.Protocol):
    @abc.abstractmethod
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse: ...


@dataclasses.dataclass(frozen=True)
class Route:
    method: str
    path: str
    handler: BaseHandler


__all__ = [
    "BaseHandler",
    "BaseRequestSchema",
    "BaseResponseSchema",
    "ErrorResponseSchema",
    "RequestValidationError",
    "Route",
]
