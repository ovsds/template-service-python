import abc
import dataclasses
import http
import typing

import aiohttp.web as aiohttp_web

import lib.utils.aiohttp.handlers.responses as aiohttp_responses
import lib.utils.json as json_utils
import lib.utils.pydantic as pydantic_utils


class RequestValidationError(Exception): ...


class BaseRequestSchema(pydantic_utils.BaseModel):
    @classmethod
    async def from_request(cls, request: aiohttp_web.Request) -> typing.Self:
        try:
            body: json_utils.JsonSerializable = {}
            if request.body_exists:
                body = json_utils.loads_bytes(await request.read())
            return cls.model_validate(
                {
                    "path": dict(request.match_info),
                    "query": dict(request.query),
                    "body": body,
                }
            )
        except ValueError as exc:
            raise RequestValidationError("Failed to parse request") from exc


class BaseResponseSchema(pydantic_utils.BaseModel):
    def as_data(self) -> typing.Any:
        return self.model_dump(mode="json")

    def as_response(self, status: int = http.HTTPStatus.OK) -> aiohttp_responses.Response:
        return aiohttp_responses.Response.with_data(data=self.as_data(), status=status)


class ErrorResponseSchema(BaseResponseSchema):
    code: str
    message: str
    status_code: int

    def as_data(self) -> typing.Any:
        return self.model_dump(mode="json", exclude={"status_code"})

    def as_error_response(self) -> aiohttp_responses.Response:
        return self.as_response(status=self.status_code)


class BaseHandler(abc.ABC):
    @abc.abstractmethod
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse: ...


class HandlerProtocol(typing.Protocol):
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse: ...


@dataclasses.dataclass(frozen=True)
class Route:
    method: str
    path: str
    handler: HandlerProtocol


__all__ = [
    "BaseHandler",
    "BaseRequestSchema",
    "BaseResponseSchema",
    "ErrorResponseSchema",
    "HandlerProtocol",
    "RequestValidationError",
    "Route",
]
