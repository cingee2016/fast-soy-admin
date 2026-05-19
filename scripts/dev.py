"""Run backend and frontend development servers together."""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import signal
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"

COMMANDS = {
    "backend": (("uv", "run", "python", "run.py"), ROOT),
    "frontend": (("pnpm", "dev"), WEB_DIR),
}

INTERRUPT_EXIT_CODES = {130, 512, -1073741510, 3221225786}


def _resolve_command(command: tuple[str, ...]) -> tuple[str, ...]:
    executable, *args = command

    if os.name == "nt":
        suffix = Path(executable).suffix
        candidates = (executable,) if suffix else (f"{executable}.exe", f"{executable}.cmd", f"{executable}.bat", executable)
    else:
        candidates = (executable,)

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return (resolved, *args)

    raise FileNotFoundError(f"Command not found: {executable}")


async def _start(name: str, command: tuple[str, ...], cwd: Path) -> asyncio.subprocess.Process:
    resolved_command = _resolve_command(command)
    print(f"[dev] starting {name}: {' '.join(command)}", flush=True)
    return await asyncio.create_subprocess_exec(*resolved_command, cwd=cwd)


async def _terminate_tree(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return

    if os.name == "nt":
        killer = await asyncio.create_subprocess_exec(
            "taskkill",
            "/PID",
            str(process.pid),
            "/T",
            "/F",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        await killer.wait()
    else:
        process.terminate()


async def _terminate(processes: list[asyncio.subprocess.Process]) -> None:
    for process in processes:
        await _terminate_tree(process)

    try:
        await asyncio.wait_for(asyncio.gather(*(process.wait() for process in processes)), timeout=8)
    except TimeoutError:
        for process in processes:
            if process.returncode is None:
                process.kill()
        await asyncio.gather(*(process.wait() for process in processes))


def _is_interrupt_exit(exit_code: int | None) -> bool:
    return exit_code in INTERRUPT_EXIT_CODES


async def main(target: str = "all") -> int:
    command_items = tuple(COMMANDS.items()) if target == "all" else ((target, COMMANDS[target]),)
    processes: list[asyncio.subprocess.Process] = []
    try:
        for name, (command, cwd) in command_items:
            processes.append(await _start(name, command, cwd))
    except Exception:
        await _terminate(processes)
        raise

    stop_event = asyncio.Event()

    def request_stop() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            pass

    wait_tasks = [asyncio.create_task(process.wait()) for process in processes]
    stop_task = asyncio.create_task(stop_event.wait())

    try:
        done, pending = await asyncio.wait([*wait_tasks, stop_task], return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        for task in [*wait_tasks, stop_task]:
            task.cancel()
        await _terminate(processes)
        return 0

    exit_code = 0
    if stop_task not in done:
        for task in done:
            exit_code = task.result()
            if _is_interrupt_exit(exit_code):
                exit_code = 0
            if exit_code != 0:
                break

    for task in pending:
        task.cancel()

    await _terminate(processes)
    return exit_code


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FastSoyAdmin development servers.")
    parser.add_argument("target", nargs="?", default="all", choices=("all", "backend", "frontend"))
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        raise SystemExit(asyncio.run(main(args.target)))
    except KeyboardInterrupt:
        raise SystemExit(0)
