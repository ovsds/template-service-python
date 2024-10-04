import tests.utils.replay as replay_utils
import tests.utils.cli as cli_utils

MANIFEST_PATH = "tests/replays.json"
RESULTS_PATH = ".test_results"
NODE_PATH = "../../node_modules"


def test_replay(replay: replay_utils.Replay):
    replay_utils.clean_replay(replay, RESULTS_PATH)
    replay_utils.build_replay(replay, RESULTS_PATH)

    cwd = f"{RESULTS_PATH}/{replay.parameters['service_slug']}"

    cli_utils.run_command("git init", cwd=cwd)
    cli_utils.run_command("task init", cwd=cwd)
    cli_utils.run_command("task dev-server-start", cwd=cwd)
    cli_utils.run_command("task dev-server-start-container", cwd=cwd)
    cli_utils.run_command(f"task lint ROOT_NENV={NODE_PATH}", cwd=cwd)
    cli_utils.run_command(f"task lint-fix ROOT_NENV={NODE_PATH}", cwd=cwd)
    cli_utils.run_command("task test", cwd=cwd)
    cli_utils.run_command("task test-container", cwd=cwd)
    cli_utils.run_command("task clean", cwd=cwd)

    replay_utils.clean_replay(replay, RESULTS_PATH)


def test_replays():
    for replay in replay_utils.read_replays(MANIFEST_PATH):
        test_replay(replay)


__all__ = [
    "test_replays",
]
