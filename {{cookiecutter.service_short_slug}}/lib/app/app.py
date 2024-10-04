import asyncio
import logging
import typing

import lib.app.errors as app_errors
import lib.app.settings as app_settings
import lib.utils.lifecycle_manager as lifecycle_manager_utils
import lib.utils.logging as logging_utils

logger = logging.getLogger(__name__)


class Application:
    def __init__(
        self,
        settings: app_settings.Settings,
        lifecycle_manager: lifecycle_manager_utils.LifecycleManager,
    ) -> None:
        self._settings = settings
        self._lifecycle_manager = lifecycle_manager

    @classmethod
    def from_settings(cls, settings: app_settings.Settings) -> typing.Self:
        # Logging

        logging_utils.initialize(
            config=logging_utils.create_config(
                log_level=settings.logs.level,
                log_format=settings.logs.format,
                loggers={
                    "asyncio": logging_utils.LoggerConfig(
                        propagate=False,
                        level=settings.logs.level,
                    ),
                    "gql.transport.aiohttp": logging_utils.LoggerConfig(
                        propagate=False,
                        level=settings.logs.level if settings.app.debug else "WARNING",
                    ),
                },
            ),
        )

        logger.info("Initializing application")

        # Clients

        logger.info("Initializing clients")

        # Repositories

        logger.info("Initializing repositories")

        # Services

        logger.info("Initializing services")

        logger.info("Initializing lifecycle manager")

        lifecycle_manager = lifecycle_manager_utils.LifecycleManager(logger=logger)

        # Startup

        # Shutdown

        logger.info("Creating application")
        application = cls(
            settings=settings,
            lifecycle_manager=lifecycle_manager,
        )

        logger.info("Initializing application finished")

        return application

    async def start(self) -> None:
        try:
            await self._lifecycle_manager.on_startup()
        except lifecycle_manager_utils.LifecycleManager.StartupError as start_error:
            logger.error("Application has failed to start")
            raise app_errors.ServerStartError("Application has failed to start, see logs above") from start_error

        logger.info("Application is starting")
        try:
            await self._start()
        except asyncio.CancelledError:
            logger.info("Application has been interrupted")
        except BaseException as unexpected_error:
            logger.exception("Application runtime error")
            raise app_errors.ServerRuntimeError("Application runtime error") from unexpected_error

    async def _start(self) -> None:
        logger.info("Application placeholder")

    async def dispose(self) -> None:
        logger.info("Application is shutting down...")

        try:
            await self._lifecycle_manager.on_shutdown()
        except lifecycle_manager_utils.LifecycleManager.ShutdownError as dispose_error:
            logger.error("Application has shut down with errors")
            raise app_errors.DisposeError("Application has shut down with errors, see logs above") from dispose_error

        logger.info("Application has successfully shut down")


__all__ = [
    "Application",
]
