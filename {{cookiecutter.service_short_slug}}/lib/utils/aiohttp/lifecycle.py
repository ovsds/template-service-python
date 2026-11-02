import asyncio
import dataclasses
import logging

import aiohttp.web as aiohttp_web

import lib.utils.lifecycle as lifecycle_utils


@dataclasses.dataclass(frozen=True)
class Lifecycle:
    logger: logging.Logger
    app: aiohttp_web.Application
    host: str
    port: int

    runner: aiohttp_web.AppRunner = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "runner", aiohttp_web.AppRunner(self.app))

    async def start_server(self) -> None:
        await self.runner.setup()
        site = aiohttp_web.TCPSite(self.runner, host=self.host, port=self.port)
        await site.start()
        self.logger.info(f"HTTP server is listening on http://{self.host}:{self.port}")

    async def serve(self) -> None:
        await asyncio.Event().wait()

    def get_startup_callbacks(self) -> list[lifecycle_utils.Callback]:
        return [
            lifecycle_utils.Callback(
                awaitable=self.start_server(),
                error_message="Failed to start HTTP server",
                success_message="HTTP server has been started",
            ),
        ]

    def get_shutdown_callbacks(self) -> list[lifecycle_utils.Callback]:
        return [
            lifecycle_utils.Callback.from_dispose(
                name="HTTP server",
                awaitable=self.runner.cleanup(),
            ),
        ]

    def get_main_task(self) -> lifecycle_utils.Task:
        return asyncio.create_task(
            coro=self.serve(),
            name="aiohttp_server",
        )


__all__ = [
    "Lifecycle",
]
