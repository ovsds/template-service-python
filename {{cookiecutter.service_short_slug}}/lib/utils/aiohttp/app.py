import dataclasses
import typing

import aiohttp.typedefs as aiohttp_typedefs
import aiohttp.web as aiohttp_web

import lib.utils.aiohttp.error_handling as error_handling
import lib.utils.aiohttp.handlers.base as handlers_base
import lib.utils.aiohttp.openapi as openapi


@dataclasses.dataclass(frozen=True)
class AppFactory:
    def create(self) -> aiohttp_web.Application:
        app = aiohttp_web.Application(middlewares=self.get_middlewares())
        routes = self.get_routes()
        openapi_info = self.get_openapi_info()
        if openapi_info is not None:
            routes = [
                *routes,
                *openapi.create_openapi_routes(
                    info=openapi_info,
                    routes=routes,
                    docs_path=self.get_openapi_docs_path(),
                ),
            ]
        for route in routes:
            app.router.add_route(route.method, route.path, route.handler.process)
        return app

    def get_routes(self) -> list[handlers_base.Route]:
        return []

    def get_middlewares(self) -> list[aiohttp_typedefs.Middleware]:
        error_handling_middleware = error_handling.ErrorHandlingMiddleware(error_map=self.get_error_map())
        return [error_handling_middleware.process]

    def get_error_map(self) -> typing.Mapping[type[Exception], handlers_base.ErrorResponseSchema]:
        return error_handling.DEFAULT_ERROR_MAP

    def get_openapi_info(self) -> openapi.OpenApiInfo | None:
        # None serves no OpenAPI spec and no Swagger UI
        return None

    def get_openapi_docs_path(self) -> str:
        return "/api/v1/docs"


__all__ = [
    "AppFactory",
]
