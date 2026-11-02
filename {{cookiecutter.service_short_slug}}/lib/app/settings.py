import warnings

import pydantic

import lib.utils.logging as logging_utils
import lib.utils.pydantic as pydantic_utils


class AppSettings(pydantic_utils.BaseSettingsModel):
    env: str = "production"
    debug: bool = False
    version: str = "unknown"

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_debug(self) -> bool:
        if not self.is_development and self.debug:
            warnings.warn("APP_DEBUG is True in non-development environment", UserWarning)

        return self.debug


class LoggingSettings(pydantic_utils.BaseSettingsModel):
    level: logging_utils.LogLevel = "INFO"
    format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"


{%- if cookiecutter.with_http_server == "true" %}


class HttpServerSettings(pydantic_utils.BaseSettingsModel):
    host: str = "0.0.0.0"
    port: int = 8080
{%- endif %}


class Settings(pydantic_utils.BaseSettings):
    app: AppSettings = pydantic.Field(default_factory=AppSettings)
    logs: LoggingSettings = pydantic.Field(default_factory=LoggingSettings)
{%- if cookiecutter.with_http_server == "true" %}
    http_server: HttpServerSettings = pydantic.Field(default_factory=HttpServerSettings)
{%- endif %}


__all__ = [
    "Settings",
]
