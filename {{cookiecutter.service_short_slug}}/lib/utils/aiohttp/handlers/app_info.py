import dataclasses

import aiohttp.web as aiohttp_web

import lib.utils.aiohttp.handlers.base as base


@dataclasses.dataclass(frozen=True)
class AppInfoHandler(base.BaseHandler):
    name: str
    version: str

    class ResponseSchema(base.BaseResponseSchema):
        name: str
        version: str

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.StreamResponse:
        return self.ResponseSchema(name=self.name, version=self.version).as_response()


__all__ = [
    "AppInfoHandler",
]
