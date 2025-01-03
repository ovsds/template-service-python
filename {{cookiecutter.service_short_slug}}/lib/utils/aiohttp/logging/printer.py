import logging
import sys
import typing

aiohttp_logger = logging.getLogger("aiohttp")


class Printer(typing.Protocol):
    def __call__(
        self,
        *args: typing.Any,
        sep: str = " ",
        end: str = "\n",
        file: typing.TextIO | None = None,
    ) -> None: ...


class PrintLogger(Printer):
    def __call__(
        self,
        *args: typing.Any,
        sep: str = " ",
        end: str = "\n",
        file: typing.TextIO | None = None,
    ) -> None:
        if file == sys.stderr:
            aiohttp_logger.error(sep.join([str(arg) for arg in args]))

        if file is None or file == sys.stdout:
            aiohttp_logger.info(sep.join([str(arg) for arg in args]))


__all__ = [
    "PrintLogger",
]
