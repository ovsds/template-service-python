import dataclasses

import lib.app.settings as app_settings
import lib.utils.aiohttp as aiohttp_utils


@dataclasses.dataclass(frozen=True)
class HttpServerAppFactory(aiohttp_utils.AppFactory):
    settings: app_settings.Settings
    readiness_service: aiohttp_utils.ReadinessService

    def get_routes(self) -> list[aiohttp_utils.Route]:
        return [
            *super().get_routes(),
            aiohttp_utils.Route(
                method="GET",
                path="/health/liveness",
                handler=aiohttp_utils.LivenessProbeHandler(),
            ),
            aiohttp_utils.Route(
                method="GET",
                path="/health/readiness",
                handler=aiohttp_utils.ReadinessProbeHandler(readiness_service=self.readiness_service),
            ),
            aiohttp_utils.Route(
                method="GET",
                path="/health/startup",
                handler=aiohttp_utils.StartupProbeHandler(readiness_service=self.readiness_service),
            ),
            aiohttp_utils.Route(
                method="GET",
                path="/api/v1/info",
                handler=aiohttp_utils.AppInfoHandler(
                    name=self.settings.app.name,
                    version=self.settings.app.version,
                ),
            ),
        ]


__all__ = [
    "HttpServerAppFactory",
]
