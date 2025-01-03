import asyncio
import dataclasses
import logging
import typing

Awaitable = typing.Awaitable[typing.Any]
Task = asyncio.Task[typing.Any]


@dataclasses.dataclass
class Callback:
    awaitable: Awaitable
    error_message: str
    success_message: str

    @classmethod
    def from_dispose(cls, name: str, awaitable: Awaitable) -> typing.Self:
        return cls(
            awaitable=awaitable,
            error_message=f"Failed to dispose {name}",
            success_message=f"{name} has been disposed",
        )


@dataclasses.dataclass(frozen=True)
class Lifecycle:
    logger: logging.Logger

    main_tasks: typing.Sequence[asyncio.Task[typing.Any]] = dataclasses.field(default_factory=list)
    startup_callbacks: typing.Sequence[Callback] = dataclasses.field(default_factory=list)
    shutdown_callbacks: typing.Sequence[Callback] = dataclasses.field(default_factory=list)

    class StartupError(Exception): ...

    class ShutdownError(Exception): ...

    async def run(self) -> None:
        if len(self.main_tasks) == 0:
            self.logger.warning("No run callbacks have been registered")
            return

        try:
            for task in asyncio.as_completed(self.main_tasks):
                await task
                raise RuntimeError("One of the main tasks has unexpectedly finished")
        except Exception:
            self.logger.error("An error occurred during the main tasks execution")

            for task in self.main_tasks:
                if not task.done():
                    continue

                if task.exception() is not None:
                    self.logger.error(f"Task {task.get_name()} has failed with exception")
                else:
                    self.logger.error(f"Task {task.get_name()} has unexpectedly finished")

            for task in self.main_tasks:
                if task.done():
                    continue

                task.cancel()
                self.logger.error(f"Task {task.get_name()} has been cancelled")

            raise

    async def on_startup(self) -> None:
        for callback in self.startup_callbacks:
            try:
                await callback.awaitable
            except Exception as error:
                self.logger.exception(callback.error_message)
                raise self.StartupError from error
            else:
                self.logger.info(callback.success_message)

    async def on_shutdown(self) -> None:
        errors: list[Exception] = []

        for callback in self.shutdown_callbacks:
            try:
                await callback.awaitable
            except Exception as error:
                errors.append(error)
                self.logger.exception(callback.error_message)
            else:
                self.logger.info(callback.success_message)

        if len(errors) != 0:
            raise self.ShutdownError


__all__ = [
    "Callback",
    "Lifecycle",
    "Task",
]
