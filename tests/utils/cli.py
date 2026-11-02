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


def _format_signal_masks(pid: str) -> str:
    # blocked, ignored and caught signals in hex, SIGINT being 0x2; SigBlk is the main thread's only
    try:
        with open(f"/proc/{pid}/status") as status:
            masks = [line.split() for line in status if line.startswith(("SigBlk:", "SigIgn:", "SigCgt:"))]
    except OSError:
        return "n/a"
    return " ".join(f"{name}{value}" for name, value in masks)


def _ps() -> list[list[str]]:
    ps = subprocess.run(["ps", "-eo", "pid,ppid,pgid,sid,stat,args"], capture_output=True, text=True, check=False)
    return [line.split(maxsplit=5) for line in ps.stdout.splitlines()]


def _descendant_groups(pid: int, processes: list[list[str]]) -> dict[int, int]:
    # by pid, as mise gives each task command a process group of its own
    children: dict[int, list[tuple[int, int]]] = {}
    for fields in processes[1:]:
        children.setdefault(int(fields[1]), []).append((int(fields[0]), int(fields[2])))
    groups = {pid: pid}
    pending = [pid]
    while pending:
        for child, group in children.get(pending.pop(), []):
            groups[child] = group
            pending.append(child)
    return groups


def _print_stop_diagnostics(pid: int, env: dict[str, str]) -> None:
    # which processes ignored the SIGINT, and in which process groups
    processes = _ps()
    tree = _descendant_groups(pid, processes)
    print(f"Processes of command {pid} and dev servers:", flush=True)
    for index, fields in enumerate(processes):
        line = " ".join(fields)
        if index == 0:
            print(f"{line} SIGNAL MASKS", flush=True)
        elif int(fields[0]) in tree or "bin.main" in line:
            print(f"{line} {_format_signal_masks(fields[0])}", flush=True)
    mise_env = {key: value for key, value in env.items() if key.startswith("MISE_") or key.startswith("__MISE")}
    print(f"mise environment of the command: {sorted(mise_env)}", flush=True)


def run_command_until_output(
    command: str,
    stop_on_output: str,
    cwd: typing.Optional[str] = None,
    envs: typing.Optional[dict[str, str]] = None,
) -> None:
    if envs is None:
        envs = {}

    print(f"Running command {command} until output {stop_on_output!r}...")
    # under `mise run test` a nested mise inherits this flag, leaves the group's signals to its parent and never
    # forwards the leader's SIGINT
    environ = {key: value for key, value in os.environ.items() if key != "MISE_TASK_PGID_MANAGED"}
    # a CI runner may start the tests with SIGINT blocked, and a child keeps the mask through exec: neither mise nor
    # the dev server would ever get the SIGINT, so the child starts with it unblocked
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    try:
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT})
        # no shell in between: the leader that gets SIGINT is the command itself, whatever /bin/sh does
        process = subprocess.Popen(
            shlex.split(command),
            cwd=cwd,
            env={**environ, **envs},
            # mise leaves a task command with a terminal on stdin in its own group, out of reach of its SIGINT
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            # a process group, not a session: a mise that leads its session shares its group with its task commands
            # and passes SIGINT only to their direct child, `sh -c`, which waits for the dev server and never passes
            # it on; leading a group only, mise gives each task command a group of its own and signals all of it
            process_group=0,
        )
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
    assert process.stdout is not None
    lines: queue.Queue[str | None] = queue.Queue()
    reader = threading.Thread(target=_read_lines, args=(process.stdout, lines), daemon=True)
    reader.start()
    # the task commands' groups, recorded while mise lives: they outlive it when it dies or is reaped first
    groups = {process.pid}
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

        print(f"Command({command}) printed {stop_on_output!r}, stopping...", flush=True)
        groups.update(_descendant_groups(process.pid, _ps()).values())
        # the leader only: mise passes it on to its task commands' groups once, docker to its container
        process.send_signal(signal.SIGINT)
        try:
            exit_code = process.wait(timeout=STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            print(f"Command({command}) did not stop in {STOP_TIMEOUT_SECONDS}s, killing...", flush=True)
            _print_stop_diagnostics(process.pid, {**environ, **envs})
            raise CommandError(exit_code=-signal.SIGKILL, stderr="", command=command) from exc

        if exit_code not in STOPPED_EXIT_CODES:
            print(f"Command({command}) failed to stop with exit_code({exit_code})")
            raise CommandError(exit_code=exit_code, stderr="", command=command)
    finally:
        if process.poll() is None:
            groups.update(_descendant_groups(process.pid, _ps()).values())
        # never the tests' own group, which a task command could join
        for group in groups - {os.getpgrp()}:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(group, signal.SIGKILL)
        process.wait()
        reader.join(timeout=STOP_TIMEOUT_SECONDS)
        while not lines.empty():
            print(lines.get() or "", end="", flush=True)


__all__ = [
    "CommandError",
    "run_command",
    "run_command_until_output",
]
