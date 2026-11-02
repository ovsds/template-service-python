import asyncio
import dataclasses
import logging
import typing

import lib.app.errors as app_errors
{%- if cookiecutter.with_http_server == "true" %}
import lib.app.http_server as app_http_server
{%- endif %}
import lib.app.settings as app_settings
{%- if cookiecutter.with_http_server == "true" %}
import lib.utils.aiohttp as aiohttp_utils
{%- endif %}
import lib.utils.lifecycle as lifecycle_utils
import lib.utils.logging as logging_utils

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class Application:
    lifecycle: lifecycle_utils.Lifecycle

    @classmethod
    def from_settings(cls, settings: app_settings.Settings) -> typing.Self:
        log_level = "DEBUG" if settings.app.is_debug else settings.logs.level
        logging_config = logging_utils.create_config(
            log_level=log_level,
            log_format=settings.logs.format,
            loggers={
                "asyncio": logging_utils.LoggerConfig(
                    propagate=False,
                    level=log_level,
                ),
            },
        )
        logging_utils.initialize(config=logging_config)
        logger.info("Logging has been initialized with config: %s", logging_config)

        logger.info("Initializing application")

        lifecycle_main_tasks: list[asyncio.Task[typing.Any]] = []
        lifecycle_startup_callbacks: list[lifecycle_utils.Callback] = []
        lifecycle_shutdown_callbacks: list[lifecycle_utils.Callback] = []

        # Global dependencies

        # Clients

        # Repositories

        # Services
{%- if cookiecutter.with_http_server == "true" %}

        # HTTP server

        logger.info("Initializing HTTP server")
        http_server_app = app_http_server.HttpServerAppFactory(settings=settings).create()
        http_server_lifecycle = aiohttp_utils.Lifecycle(
            logger=logger,
            app=http_server_app,
            host=settings.http_server.host,
            port=settings.http_server.port,
        )
        lifecycle_main_tasks.append(http_server_lifecycle.get_main_task())
        lifecycle_startup_callbacks.extend(http_server_lifecycle.get_startup_callbacks())
        lifecycle_shutdown_callbacks.extend(http_server_lifecycle.get_shutdown_callbacks())
{%- endif %}

        logger.info("Initializing lifecycle manager")

        lifecycle = lifecycle_utils.Lifecycle(
            logger=logger,
            main_tasks=lifecycle_main_tasks,
            startup_callbacks=lifecycle_startup_callbacks,
            shutdown_callbacks=list(reversed(lifecycle_shutdown_callbacks)),
        )

        logger.info("Creating application")
        application = cls(
            lifecycle=lifecycle,
        )

        logger.info("Initializing application finished")

        return application

    async def start(self) -> None:
        try:
            await self.lifecycle.on_startup()
        except lifecycle_utils.Lifecycle.StartupError as start_error:
            logger.error("Application has failed to start")
            raise app_errors.ServerStartError("Application has failed to start, see logs above") from start_error

        logger.info("Application is starting")
        try:
            await self.lifecycle.run()
        except asyncio.CancelledError:
            logger.info("Application has been interrupted")
        except BaseException as unexpected_error:
            logger.exception("Application runtime error")
            raise app_errors.ServerRuntimeError("Application runtime error") from unexpected_error

    async def dispose(self) -> None:
        logger.info("Application is shutting down...")

        try:
            await self.lifecycle.on_shutdown()
        except lifecycle_utils.Lifecycle.ShutdownError as dispose_error:
            logger.error("Application has shut down with errors")
            raise app_errors.DisposeError("Application has shut down with errors, see logs above") from dispose_error

        logger.info("Application has successfully shut down")


__all__ = [
    "Application",
]
