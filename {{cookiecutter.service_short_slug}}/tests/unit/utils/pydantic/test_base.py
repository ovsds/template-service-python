import pydantic
import pytest

import lib.utils.pydantic as pydantic_utils


class BaseAnimal(pydantic_utils.TypedBaseModel): ...


class Cat(BaseAnimal):
    type_name: str = pydantic.Field(default="cat", alias="type")


BaseAnimal.register("cat", Cat)


class BaseColor(pydantic_utils.TypedBaseModel): ...


class Red(BaseColor):
    type_name: str = pydantic.Field(default="red", alias="type")


BaseColor.register("red", Red)


def test_factory_keeps_registrations_after_another_typed_class():
    assert isinstance(BaseAnimal.factory({"type": "cat"}), Cat)
    assert isinstance(BaseColor.factory({"type": "red"}), Red)


def test_factory_does_not_share_registrations_between_classes():
    with pytest.raises(ValueError, match="Unknown type: red"):
        BaseAnimal.factory({"type": "red"})
