import typing

import orjson

JsonSerializableType = str | int | float | bool | None
JsonSerializable = JsonSerializableType | typing.Mapping[str, "JsonSerializable"] | typing.Sequence["JsonSerializable"]
JsonSerializableDict = typing.Mapping[str, JsonSerializable]
JsonSerializableList = typing.Sequence[JsonSerializable]


dumps_bytes = orjson.dumps
loads_bytes = orjson.loads


def dumps_str(obj: JsonSerializable) -> str:
    return dumps_bytes(obj).decode("utf-8")


def loads_str(s: str) -> JsonSerializable:
    return loads_bytes(s.encode("utf-8"))


__all__ = [
    "JsonSerializable",
    "JsonSerializableDict",
    "JsonSerializableList",
    "JsonSerializableType",
    "dumps_bytes",
    "dumps_str",
    "loads_bytes",
    "loads_str",
]
