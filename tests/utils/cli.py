import contextlib
import os
import queue
import shlex
import signal
import subprocess
import threading
import time
import typing

START_TIMEOUT_SECONDS = 900
STOP_TIMEOUT_SECONDS = 30
STOPPED_EXIT_CODES = (0, 128 + signal.SIGINT, -signal.SIGINT)


class CommandError(Exception):
    def __init__(self, exit_code: int, stderr: str, command: str):
        self.exit_code = exit_code
        self.stderr = stderr
        self.command = command


def run_command(
    command: str,
    cwd: typing.Optional[str] = None,
    envs: typing.Optional[dict[str, str]] = None,
) -> None:
    if envs is None:
        envs = {}

    print(f"Running command {command}...")
    try:
        subprocess.run(command, cwd=cwd, check=True, shell=True, env={**os.environ, **envs})
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8") if exc.stderr else ""
        exit_code = exc.returncode
        print(f"Command({command}) failed with exit_code({exit_code}) stderr:")
        print(stderr)

        raise CommandError(
            exit_code=exit_code,
            stderr=stderr,
            command=command,
        ) from exc


def _read_lines(lines: typing.Iterable[str], output: "queue.Queue[str | None]") -> None:
    for line in lines:
        output.put(line)
    output.put(None)


def run_command_until_output(
    command: str,
    stop_on_output: str,
    cwd: typing.Optional[str] = None,
    envs: typing.Optional[dict[str, str]] = None,
) -> None:
    if envs is None:
        envs = {}

    print(f"Running command {command} until output {stop_on_output!r}...")
    # the command gets a session of its own, yet under `mise run test` a nested mise inherits this flag, leaves the
    # group's signals to its parent and never forwards the leader's SIGINT
    environ = {key: value for key, value in os.environ.items() if key != "MISE_TASK_PGID_MANAGED"}
    # no shell in between: a /bin/sh that does not exec its command (dash) keeps the leader's SIGINT to itself
    process = subprocess.Popen(
        shlex.split(command),
        cwd=cwd,
        env={**environ, **envs},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    assert process.stdout is not None
    lines: queue.Queue[str | None] = queue.Queue()
    reader = threading.Thread(target=_read_lines, args=(process.stdout, lines), daemon=True)
    reader.start()
    deadline = time.monotonic() + START_TIMEOUT_SECONDS
    try:
        while True:
            try:
                line = lines.get(timeout=max(deadline - time.monotonic(), 0))
            except queue.Empty as exc:
                print(f"Command({command}) printed no {stop_on_output!r} in {START_TIMEOUT_SECONDS}s")
                raise CommandError(exit_code=-signal.SIGKILL, stderr="", command=command) from exc

            if line is None:
                exit_code = process.wait()
                if exit_code != 0:
                    print(f"Command({command}) failed with exit_code({exit_code})")
                    raise CommandError(exit_code=exit_code, stderr="", command=command)
                return

            print(line, end="", flush=True)
            if stop_on_output in line:
                break

        print(f"Command({command}) printed {stop_on_output!r}, stopping...")
        # the leader only: mise and docker forward the signal to their child once
        process.send_signal(signal.SIGINT)
        try:
            exit_code = process.wait(timeout=STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            print(f"Command({command}) did not stop in {STOP_TIMEOUT_SECONDS}s, killing...")
            raise CommandError(exit_code=-signal.SIGKILL, stderr="", command=command) from exc

        if exit_code not in STOPPED_EXIT_CODES:
            print(f"Command({command}) failed to stop with exit_code({exit_code})")
            raise CommandError(exit_code=exit_code, stderr="", command=command)
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        reader.join(timeout=STOP_TIMEOUT_SECONDS)
        while not lines.empty():
            print(lines.get() or "", end="", flush=True)


__all__ = [
    "CommandError",
    "run_command",
    "run_command_until_output",
]
