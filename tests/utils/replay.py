import dataclasses
import os
import shutil
import typing

import json

import tests.utils.cli as cli_utils

DEFAULT_RESULTS_PATH = ".test_results"


@dataclasses.dataclass
class Replay:
    name: str
    parameters: dict[str, str]

    @classmethod
    def from_dict(cls, replay_dict: dict[str, typing.Any]) -> "Replay":
        return cls(
            name=replay_dict["name"],
            parameters=replay_dict["parameters"],
        )


@dataclasses.dataclass
class ReplaysManifest:
    default_parameters: dict[str, str]
    replays: list[Replay]

    @classmethod
    def from_dict(cls, replays_dict: dict[str, typing.Any]) -> "ReplaysManifest":
        return cls(
            default_parameters=replays_dict["default_parameters"],
            replays=[Replay.from_dict(replay_dict) for replay_dict in replays_dict["replays"]],
        )

    @classmethod
    def from_json_file(cls, path: str) -> "ReplaysManifest":
        with open(path, encoding="utf-8") as file:
            raw_manifest = json.load(file)
            return cls.from_dict(raw_manifest)


def read_replays(manifest_path: str) -> typing.Iterable[Replay]:
    print(f"Reading manifest on {manifest_path}")
    manifest = ReplaysManifest.from_json_file(manifest_path)

    for replay in manifest.replays:
        print(f"{replay.name}: Starting...")
        params = manifest.default_parameters.copy()
        params.update(replay.parameters)
        yield Replay(name=replay.name, parameters=params)
        print(f"{replay.name}: Finished")


def build_replay(replay: Replay, results_path: str = DEFAULT_RESULTS_PATH):
    print(f"{replay.name}: Building replay...")
    extra_parameters = [f"{key}=\"{value}\"" for key, value in replay.parameters.items()]
    cli_utils.run_command(f"cookiecutter --output-dir {results_path} --no-input . {' '.join(extra_parameters)}")


def clean_replay(replay: Replay, results_path: str = DEFAULT_RESULTS_PATH):
    if not os.path.isdir(results_path):
        return

    print(f"{replay.name}: Cleaning results directory...")
    shutil.rmtree(results_path)


__all__ = [
    "Replay",
    "build_replay",
    "clean_replay",
    "read_replays",
]
