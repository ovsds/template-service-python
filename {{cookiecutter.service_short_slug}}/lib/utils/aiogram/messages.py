import typing


def escape_symbols(string: str, symbols: typing.Iterable[str]) -> str:
    result = string

    for character in symbols:
        result = result.replace(character, f"\\{character}")

    return result


__all__ = [
    "escape_symbols",
]
