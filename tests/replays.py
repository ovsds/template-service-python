import tests.utils.replay as replay_utils

MANIFEST_PATH = "tests/replays.json"
ADDITIONAL_FILES_PATH = "tests/additional_files"
RESULTS_PATH = ".test_results"


def test_replay(replay: replay_utils.Replay):
    cwd = f"{RESULTS_PATH}/{replay.parameters['service_slug']}"

    replay_utils.clean_replay(replay, RESULTS_PATH)
    replay_utils.build_replay(replay, RESULTS_PATH)
    replay_utils.copy_additional_files(replay, ADDITIONAL_FILES_PATH, cwd)
    replay_utils.run_replay(replay, cwd)
    replay_utils.clean_replay(replay, RESULTS_PATH)


def test_replays():
    for replay in replay_utils.read_replays(MANIFEST_PATH):
        test_replay(replay)


__all__ = [
    "test_replays",
]
