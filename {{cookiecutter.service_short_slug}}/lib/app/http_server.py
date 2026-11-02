import dataclasses
{%- if cookiecutter.with_prometheus == "true" %}

import aiohttp.typedefs as aiohttp_typedefs
{%- endif %}

import lib.app.settings as app_settings
import lib.utils.aiohttp as aiohttp_utils


@dataclasses.dataclass(frozen=True)
class HttpServerAppFactory(aiohttp_utils.AppFactory):
    settings: app_settings.Settings
    readiness_service: aiohttp_utils.ReadinessService
{%- if cookiecutter.with_prometheus == "true" %}
    request_metrics: aiohttp_utils.RequestMetrics
{%- endif %}

    def get_routes(self) -> list[aiohttp_utils.Route]:
        return [
            *super().get_routes(),
            aiohttp_utils.Route(
                method="GET",
                path="/health/liveness",
                handler=aiohttp_utils.LivenessProbeHandler(),
                openapi_tags=["health"],
                openapi_summary="Liveness probe",
            ),
            aiohttp_utils.Route(
                method="GET",
                path="/health/readiness",
                handler=aiohttp_utils.ReadinessProbeHandler(readiness_service=self.readiness_service),
                openapi_tags=["health"],
                openapi_summary="Readiness probe: every readiness-required subsystem is ready",
            ),
            aiohttp_utils.Route(
                method="GET",
                path="/health/startup",
                handler=aiohttp_utils.StartupProbeHandler(readiness_service=self.readiness_service),
                openapi_tags=["health"],
                openapi_summary="Startup probe: every startup-required subsystem is ready",
            ),
            aiohttp_utils.Route(
                method="GET",
                path="/api/v1/info",
                handler=aiohttp_utils.AppInfoHandler(
                    name=self.settings.app.name,
                    version=self.settings.app.version,
                ),
                openapi_tags=["app"],
                openapi_summary="Application name and version",
            ),
{%- if cookiecutter.with_prometheus == "true" %}
            aiohttp_utils.Route(
                method="GET",
                path="/metrics",
                handler=aiohttp_utils.MetricsHandler(registry=self.request_metrics.registry),
                openapi_include=False,
            ),
{%- endif %}
        ]
{%- if cookiecutter.with_prometheus == "true" %}

    def get_middlewares(self) -> list[aiohttp_typedefs.Middleware]:
        # Metrics go outermost, so they count the responses the error handling middleware renders
        request_metrics_middleware = aiohttp_utils.RequestMetricsMiddleware(metrics=self.request_metrics)
        return [request_metrics_middleware.process, *super().get_middlewares()]
{%- endif %}

    def get_openapi_info(self) -> aiohttp_utils.OpenApiInfo:
        return aiohttp_utils.OpenApiInfo(title=self.settings.app.name, version=self.settings.app.version)


__all__ = [
    "HttpServerAppFactory",
]
