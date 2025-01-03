import asyncio
import dataclasses
import logging
import typing

import lib.app.errors as app_errors
import lib.app.settings as app_settings
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

        logger.info("Initializing global dependencies")

        logger.info("Initializing clients")

        logger.info("Initializing repositories")

        logger.info("Initializing services")

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
