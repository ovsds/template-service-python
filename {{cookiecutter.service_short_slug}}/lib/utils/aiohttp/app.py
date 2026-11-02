import dataclasses
import typing

import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web

import lib.utils.aiohttp.error_handling as error_handling
import lib.utils.aiohttp.handlers.base as handlers_base


@dataclasses.dataclass(frozen=True)
class AppFactory:
    def create(self) -> aiohttp_web.Application:
        app = aiohttp_web.Application(middlewares=self.get_middlewares())
        for route in self.get_routes():
            app.router.add_route(route.method, route.path, route.handler.process)
        return app

    def get_routes(self) -> list[handlers_base.Route]:
        return []

    def get_middlewares(self) -> list[aiohttp_typedefs.Middleware]:
        error_handling_middleware = error_handling.ErrorHandlingMiddleware(error_map=self.get_error_map())
        return [error_handling_middleware.process]

    def get_error_map(self) -> typing.Mapping[type[Exception], handlers_base.ErrorResponseSchema]:
        return error_handling.DEFAULT_ERROR_MAP


__all__ = [
    "AppFactory",
]
