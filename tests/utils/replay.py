import dataclasses
import os
import shutil
import typing

import json

import tests.utils.cli as cli_utils

DEFAULT_RESULTS_PATH = ".test_results"


@dataclasses.dataclass(frozen=True)
class Command:
    command: str
    stop_on_output: typing.Optional[str] = None

    @classmethod
    def from_raw(cls, raw_command: typing.Union[str, dict[str, str]]) -> "Command":
        if isinstance(raw_command, str):
            return cls(command=raw_command)
        return cls(
            command=raw_command["command"],
            stop_on_output=raw_command.get("stop_on_output"),
        )


@dataclasses.dataclass(frozen=True)
class Replay:
    name: str
    parameters: dict[str, str]
    additional_files: list[str] = dataclasses.field(default_factory=list)
    commands: list[Command] = dataclasses.field(default_factory=list)
    envs: dict[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_dict(cls, replay_dict: dict[str, typing.Any]) -> "Replay":
        return cls(
            name=replay_dict["name"],
            parameters=replay_dict["parameters"],
            additional_files=replay_dict.get("additional_files", []),
            commands=[Command.from_raw(command) for command in replay_dict.get("commands", [])],
            envs=replay_dict.get("envs", {}),
        )

    def evolve(self, **kwargs) -> "Replay":
        return dataclasses.replace(self, **kwargs)


@dataclasses.dataclass(frozen=True)
class ReplaysManifest:
    default_parameters: dict[str, str]
    commands: list[Command]
    replays: list[Replay]

    @classmethod
    def from_dict(cls, replays_dict: dict[str, typing.Any]) -> "ReplaysManifest":
        return cls(
            default_parameters=replays_dict["default_parameters"],
            commands=[Command.from_raw(command) for command in replays_dict["commands"]],
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
        parameters = manifest.default_parameters.copy()
        parameters.update(replay.parameters)
        if replay.commands:
            raise ValueError(f"{replay.name}: Replay has commands, but it should not have any")
        yield replay.evolve(parameters=parameters, commands=manifest.commands)
        print(f"{replay.name}: Finished")


def build_replay(replay: Replay, results_path: str = DEFAULT_RESULTS_PATH):
    print(f"{replay.name}: Building replay...")
    extra_parameters = [f"{key}=\"{value}\"" for key, value in replay.parameters.items()]
    cli_utils.run_command(f"cookiecutter --output-dir {results_path} --no-input . {' '.join(extra_parameters)}")


def run_replay(replay: Replay, cwd: str):
    for command in replay.commands:
        if command.stop_on_output is None:
            cli_utils.run_command(command.command, cwd=cwd, envs=replay.envs)
        else:
            cli_utils.run_command_until_output(
                command.command,
                stop_on_output=command.stop_on_output,
                cwd=cwd,
                envs=replay.envs,
            )


def copy_additional_files(replay: Replay, additional_files_path: str, results_path: str = DEFAULT_RESULTS_PATH):
    for additional_file in replay.additional_files:
        source_path = os.path.join(additional_files_path, additional_file)
        if source_path.endswith("/"):
            print(f"{replay.name}: Copying additional directory {additional_file}...")
            shutil.copytree(source_path, os.path.join(results_path, additional_file))
        else:
            print(f"{replay.name}: Copying additional file {additional_file}...")
            shutil.copy(source_path, results_path)


def clean_replay(replay: Replay, results_path: str = DEFAULT_RESULTS_PATH):
    if not os.path.isdir(results_path):
        return

    print(f"{replay.name}: Cleaning results directory...")
    shutil.rmtree(results_path)


__all__ = [
    "Command",
    "Replay",
    "build_replay",
    "clean_replay",
    "copy_additional_files",
    "read_replays",
    "run_replay",
]
