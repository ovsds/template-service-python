import http
import typing

import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web

import lib.utils.json as json_utils


class Response(aiohttp_web.Response):
    @classmethod
    def with_bytes(
        cls,
        body: bytes,
        status: int = http.HTTPStatus.OK,
        reason: str | None = None,
        headers: aiohttp_typedefs.LooseHeaders | None = None,
        content_type: str | None = None,
    ) -> typing.Self:
        return cls(
            body=body,
            status=status,
            reason=reason,
            headers=headers,
            content_type=content_type,
        )

    @classmethod
    def with_text(
        cls,
        text: str,
        status: int = http.HTTPStatus.OK,
        reason: str | None = None,
        headers: aiohttp_typedefs.LooseHeaders | None = None,
        content_type: str | None = None,
    ) -> typing.Self:
        return cls(
            text=text,
            status=status,
            reason=reason,
            headers=headers,
            content_type=content_type,
        )

    @classmethod
    def with_data(
        cls,
        data: typing.Any,
        status: int = http.HTTPStatus.OK,
        reason: str | None = None,
        headers: aiohttp_typedefs.LooseHeaders | None = None,
    ) -> typing.Self:
        body = json_utils.dumps_bytes(data)
        return cls.with_bytes(
            body=body,
            status=status,
            reason=reason,
            headers=headers,
            content_type="application/json",
        )

    @classmethod
    def with_error(cls, status: int, problem: str, message: str, details: typing.Any = None) -> typing.Self:
        data = {"code": f"{status}_{problem}", "message": message}
        if details is not None:
            data["details"] = details
        return cls.with_data(status=status, data=data)


__all__ = [
    "Response",
]
