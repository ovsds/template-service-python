import os
import pathlib
import typing

import pydantic_settings

import lib.utils.pydantic.base as base

T = typing.TypeVar("T")
T_key = typing.TypeVar("T_key")
T_value = typing.TypeVar("T_value")


class EnvExpandedYamlConfigSettingsSource(pydantic_settings.YamlConfigSettingsSource):
    def _populate(self, data: T) -> T:
        if isinstance(data, dict):
            return self._populate_dict(data)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
        elif isinstance(data, list):
            return self._populate_list(data)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
        elif isinstance(data, str):
            return os.path.expandvars(data)
        else:
            return data

    def _populate_dict(self, data: dict[T_key, T_value]) -> dict[T_key, T_value]:
        return {key: self._populate(value) for key, value in data.items()}

    def _populate_list(self, data: list[T]) -> list[T]:
        return [self._populate(value) for value in data]

    def _read_file(self, file_path: pathlib.Path) -> dict[str, typing.Any]:
        result = super()._read_file(file_path)
        return self._populate_dict(result)


class BaseSettingsModel(base.BaseModel): ...


class TypedBaseSettingsModel(base.TypedBaseModel, BaseSettingsModel): ...


class BaseSettings(pydantic_settings.BaseSettings):
    SETTINGS_PATH: typing.ClassVar[str] = "SETTINGS_PATH"

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
            *cls.get_settings_yaml_sources(
                settings_cls,
                cls.SETTINGS_PATH,
            ),
        )

    @classmethod
    def get_settings_yaml_sources(
        cls,
        settings_cls: type[pydantic_settings.BaseSettings],
        settings_yaml_env: str,
    ) -> typing.Sequence[pydantic_settings.YamlConfigSettingsSource]:
        setting_yaml_env = os.environ.get(settings_yaml_env, None)

        if setting_yaml_env is None:
            return []

        paths = setting_yaml_env.split(":")

        for path in paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Settings file not found: {path}")

        return [
            EnvExpandedYamlConfigSettingsSource(
                settings_cls,
                yaml_file=path,
            )
            for path in paths
        ]


__all__ = [
    "BaseSettings",
    "BaseSettingsModel",
    "EnvExpandedYamlConfigSettingsSource",
    "TypedBaseSettingsModel",
]
