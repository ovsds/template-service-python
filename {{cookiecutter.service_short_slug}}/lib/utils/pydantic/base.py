import typing

import pydantic
import pydantic._internal._model_construction as pydantic_model_construction
import pydantic.fields


class BaseModel(pydantic.BaseModel): ...


class TypedMeta(pydantic_model_construction.ModelMetaclass, type[BaseModel]):
    def __new__(
        cls,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> type[BaseModel]:
        cls._classes: dict[str, typing.Any] = {}
        return super().__new__(cls, *args, **kwargs)


class TypedBaseModel(BaseModel, metaclass=TypedMeta):
    type_name: str = pydantic.fields.Field(alias="type")

    @classmethod
    def register(cls, name: str, class_: type) -> None:
        if name in cls._classes:  # pyright: ignore[reportPrivateUsage]
            raise ValueError(f"Class with name '{name}' already registered")

        if not issubclass(class_, cls):
            raise ValueError(f"Class '{class_}' must be subclass of '{cls}'")

        cls._classes[name] = class_  # pyright: ignore[reportPrivateUsage]

    @classmethod
    def factory(cls, data: typing.Any) -> typing.Self:
        if isinstance(data, cls):
            return data

        if not isinstance(data, dict):
            raise ValueError("Data must be dict")

        type_key = cls.model_fields["type_name"].alias or "type_name"
        if type_key not in data:
            raise ValueError(f"Data must contain '{type_key}' key")

        class_name = data[type_key]  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(class_name, str):
            raise ValueError("Type must be string")

        if class_name not in cls._classes:  # pyright: ignore[reportPrivateUsage]
            raise ValueError(f"Unknown type: {class_name}")

        class_ = cls._classes[class_name]  # pyright: ignore[reportPrivateUsage]

        return class_.model_validate(data)

    @classmethod
    def list_factory(cls, data: typing.Any) -> list[BaseModel]:
        if not isinstance(data, typing.Sequence):
            raise ValueError("Data must be sequence for list factory")

        result: list[BaseModel] = []
        for item in data:  # pyright: ignore[reportUnknownVariableType]
            result.append(cls.factory(item))

        return result

    @classmethod
    def dict_factory(cls, data: typing.Any) -> dict[str, BaseModel]:
        if not isinstance(data, typing.Mapping):
            raise ValueError("Data must be mapping for dict factory")

        result: dict[str, BaseModel] = {}
        for key, value in data.items():  # pyright: ignore[reportUnknownVariableType]
            if not isinstance(key, str):
                raise ValueError("Key must be string")

            result[key] = cls.factory(value)

        return result


TypedBaseModelT = typing.TypeVar("TypedBaseModelT", bound=TypedBaseModel)

if typing.TYPE_CHECKING:
    TypedAnnotation = typing.Annotated[TypedBaseModelT, ...]
    TypedListAnnotation = typing.Annotated[list[TypedBaseModelT], ...]
    TypedDictAnnotation = typing.Annotated[dict[str, TypedBaseModelT], ...]
else:

    class TypedAnnotation:
        def __class_getitem__(cls, base_class: TypedBaseModel) -> typing.Any:
            return typing.Annotated[
                pydantic.SerializeAsAny[base_class],
                pydantic.BeforeValidator(base_class.factory),
            ]

    class TypedListAnnotation:
        def __class_getitem__(cls, base_class: TypedBaseModel) -> typing.Any:
            return typing.Annotated[
                list[pydantic.SerializeAsAny[base_class]],
                pydantic.BeforeValidator(base_class.list_factory),
            ]

    class TypedDictAnnotation:
        def __class_getitem__(cls, base_class: TypedBaseModel) -> typing.Any:
            return typing.Annotated[
                dict[str, pydantic.SerializeAsAny[base_class]],
                pydantic.BeforeValidator(base_class.dict_factory),
            ]


__all__ = [
    "BaseModel",
    "TypedAnnotation",
    "TypedBaseModel",
    "TypedDictAnnotation",
    "TypedListAnnotation",
]
