import dataclasses
import typing

import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web

import lib.utils.aiohttp.error_handling as error_handling
import lib.utils.aiohttp.handlers.base as handlers_base
import lib.utils.aiohttp.request_context as request_context
import lib.utils.aiohttp.request_logging as request_logging


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
        request_context_middleware = request_context.RequestContextMiddleware()
        request_logging_middleware = request_logging.RequestLoggingMiddleware()
        error_handling_middleware = error_handling.ErrorHandlingMiddleware(error_map=self.get_error_map())
        # Request context goes outermost, so the request log and error responses carry the request ID
        return [
            request_context_middleware.process,
            request_logging_middleware.process,
            error_handling_middleware.process,
        ]

    def get_error_map(self) -> typing.Mapping[type[Exception], handlers_base.ErrorResponseSchema]:
        return error_handling.DEFAULT_ERROR_MAP


__all__ = [
    "AppFactory",
]
