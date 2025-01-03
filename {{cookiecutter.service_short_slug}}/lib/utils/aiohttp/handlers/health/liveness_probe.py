import logging

import aiohttp.web as aiohttp_web

import lib.utils.aiohttp as aiohttp_utils

logger = logging.getLogger(__name__)


class LivenessProbeHandler:
    async def process(self, request: aiohttp_web.Request) -> aiohttp_web.Response:
        return aiohttp_utils.Response.with_data(
            status=200,
            data={"status": "healthy"},
        )


__all__ = [
    "LivenessProbeHandler",
]
