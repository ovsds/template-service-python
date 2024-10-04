import subprocess
import typing


class CommandError(Exception):
    def __init__(self, exit_code: int, stderr: str, command: str):
        self.exit_code = exit_code
        self.stderr = stderr
        self.command = command


def run_command(command: str, cwd: typing.Optional[str] = None) -> None:
    print(f"Running command {command}...")
    try:
        subprocess.run(command, cwd=cwd, check=True, shell=True)
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


__all__ = [
    "CommandError",
    "run_command",
]
