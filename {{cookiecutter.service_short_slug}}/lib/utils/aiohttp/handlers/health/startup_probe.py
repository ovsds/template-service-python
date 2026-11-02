import dataclasses
import logging

import aiohttp.web as aiohttp_web

import lib.utils.aiohttp as aiohttp_utils
import lib.utils.aiohttp.handlers.health.service as health_service

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class StartupProbeHandler:
    readiness_service: health_service.ReadinessService

    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.Response:
        statuses = await self.readiness_service.get_statuses()
        subsystems_status = {
            name: {"value": status.value, "required": status.startup_required}
            for name, status in statuses.statuses.items()
        }

        if statuses.is_startup_ready():
            return aiohttp_utils.Response.with_data(
                status=200,
                data={"status": "healthy", "subsystems_status": subsystems_status},
            )

        logger.error("Not all required subsystems are started!", extra={"subsystems_status": subsystems_status})

        return aiohttp_utils.Response.with_data(
            status=500,
            data={"status": "unhealthy", "subsystems_status": subsystems_status},
        )


__all__ = [
    "StartupProbeHandler",
]
