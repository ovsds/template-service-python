import dataclasses
import logging
import typing

Callback = typing.Awaitable[typing.Any] | typing.Callable[[], typing.Any]


@dataclasses.dataclass
class ShutdownCallback:
    callback: Callback
    error_message: str
    success_message: str

    @classmethod
    def from_disposable_resource(cls, name: str, dispose_callback: Callback) -> typing.Self:
        return cls(
            callback=dispose_callback,
            error_message=f"Failed to dispose {name}",
            success_message=f"{name} has been disposed",
        )


@dataclasses.dataclass
class StartupCallback:
    callback: Callback
    error_message: str
    success_message: str


class LifecycleManager:
    class StartupError(Exception): ...

    class ShutdownError(Exception): ...

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

        self._startup_callbacks: list[StartupCallback] = []
        self._shutdown_callbacks: list[ShutdownCallback] = []

    def add_startup_callback(self, callback: StartupCallback) -> None:
        self._startup_callbacks.append(callback)

    async def on_startup(self) -> None:
        for callback in self._startup_callbacks:
            try:
                if isinstance(callback.callback, typing.Awaitable):
                    await callback.callback
                else:
                    callback.callback()
            except Exception as error:
                self._logger.exception(callback.error_message)
                raise self.StartupError from error
            else:
                self._logger.info(callback.success_message)

    def add_shutdown_callback(self, callback: ShutdownCallback) -> None:
        self._shutdown_callbacks.append(callback)

    async def on_shutdown(self) -> None:
        errors: list[Exception] = []

        for callback in self._shutdown_callbacks:
            try:
                if isinstance(callback.callback, typing.Awaitable):
                    await callback.callback
                else:
                    callback.callback()
            except Exception as error:
                errors.append(error)
                self._logger.exception(callback.error_message)
            else:
                self._logger.info(callback.success_message)

        if len(errors) != 0:
            raise self.ShutdownError


__all__ = [
    "LifecycleManager",
    "ShutdownCallback",
    "StartupCallback",
]
