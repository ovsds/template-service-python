import os
import signal
import subprocess
import threading
import typing

STOP_TIMEOUT_SECONDS = 30


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


def _print_lines(lines: typing.Iterable[str]) -> None:
    for line in lines:
        print(line, end="", flush=True)


def run_command_until_output(
    command: str,
    stop_on_output: str,
    cwd: typing.Optional[str] = None,
    envs: typing.Optional[dict[str, str]] = None,
) -> None:
    if envs is None:
        envs = {}

    print(f"Running command {command} until output {stop_on_output!r}...")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        shell=True,
        env={**os.environ, **envs},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    assert process.stdout is not None
    try:
        for line in process.stdout:
            print(line, end="", flush=True)
            if stop_on_output in line:
                break
        else:
            exit_code = process.wait()
            if exit_code != 0:
                print(f"Command({command}) failed with exit_code({exit_code})")
                raise CommandError(exit_code=exit_code, stderr="", command=command)
            return

        print(f"Command({command}) printed {stop_on_output!r}, stopping...")
        threading.Thread(target=_print_lines, args=(process.stdout,), daemon=True).start()
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            print(f"Command({command}) did not stop in {STOP_TIMEOUT_SECONDS}s, killing...")
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise CommandError(exit_code=-signal.SIGKILL, stderr="", command=command) from exc
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


__all__ = [
    "CommandError",
    "run_command",
    "run_command_until_output",
]
