import dataclasses
import logging
import typing

import aiohttp.web as aiohttp_web

import lib.utils.aiohttp as aiohttp_utils

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class SubsystemReadinessCallback:
    name: str
    is_ready: typing.Callable[[], typing.Awaitable[bool]]


@dataclasses.dataclass(frozen=True)
class ReadinessProbeHandler:
    subsystems: typing.Sequence[SubsystemReadinessCallback]

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.Response:
        subsystems_status: dict[str, bool] = {}

        for subsystem in self.subsystems:
            is_ready = await subsystem.is_ready()
            subsystems_status[subsystem.name] = is_ready

        if all(subsystems_status.values()):
            return aiohttp_utils.Response.with_data(
                status=200,
                data={"status": "healthy"},
            )

        logger.error("Not all subsystems are healthy!", extra=subsystems_status)

        return aiohttp_utils.Response.with_data(
            status=500,
            data={"status": "unhealthy", "subsystems_status": subsystems_status},
        )


__all__ = [
    "ReadinessProbeHandler",
    "SubsystemReadinessCallback",
]
