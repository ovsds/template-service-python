import os

import tests.utils.replay as replay_utils
import tests.utils.cli as cli_utils

MANIFEST_PATH = "tests/replays.json"
RESULTS_PATH = ".test_results"
NODE_BIN_PATH = "node_modules/.bin"


def test_replay(replay: replay_utils.Replay):
    replay_utils.clean_replay(replay, RESULTS_PATH)
    replay_utils.build_replay(replay, RESULTS_PATH)

    cwd = f"{RESULTS_PATH}/{replay.parameters['service_slug']}"
    #
    # cli_utils.run_command("git init", cwd=cwd)
    # cli_utils.run_command("task init", cwd=cwd)
    # cli_utils.run_command("task lint", cwd=cwd)
    # cli_utils.run_command("task lint-fix", cwd=cwd)
    # cli_utils.run_command("task clean", cwd=cwd)

    replay_utils.clean_replay(replay, RESULTS_PATH)


def test_replays():
    for replay in replay_utils.read_replays(MANIFEST_PATH):
        test_replay(replay)


__all__ = [
    "test_replays",
]
