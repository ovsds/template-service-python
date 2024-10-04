import warnings

import pydantic
import pydantic_settings

import lib.utils.logging as logging_utils


class AppSettings(pydantic_settings.BaseSettings):
    env: str = "production"
    debug: bool = False

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_debug(self) -> bool:
        if not self.is_development:
            warnings.warn("APP_DEBUG is True in non-development environment", UserWarning)

        return self.debug


class LoggingSettings(pydantic_settings.BaseSettings):
    level: logging_utils.LogLevel = "INFO"
    format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"


class Settings(pydantic_settings.BaseSettings):
    app: AppSettings = pydantic.Field(default_factory=AppSettings)
    logs: LoggingSettings = pydantic.Field(default_factory=LoggingSettings)

    model_config = pydantic_settings.SettingsConfigDict(
        env_nested_delimiter="__",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[pydantic_settings.BaseSettings],
        init_settings: pydantic_settings.PydanticBaseSettingsSource,
        env_settings: pydantic_settings.PydanticBaseSettingsSource,
        dotenv_settings: pydantic_settings.PydanticBaseSettingsSource,
        file_secret_settings: pydantic_settings.PydanticBaseSettingsSource,
    ) -> tuple[pydantic_settings.PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            pydantic_settings.YamlConfigSettingsSource(
                settings_cls,
            ),
        )


__all__ = [
    "AppSettings",
    "LoggingSettings",
    "Settings",
]
