"""Launcher macOS: scollega la GUI e chiude il Terminale del file .command."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path


APPLE_SCRIPT_LINES = (
    "on run argv",
    "set launcherTTY to item 1 of argv",
    'tell application "Terminal"',
    "repeat with terminalWindow in windows",
    "repeat with terminalTab in tabs of terminalWindow",
    "if tty of terminalTab is launcherTTY then",
    "if (count of tabs of terminalWindow) > 1 then",
    "close terminalTab",
    "else",
    "close terminalWindow",
    "end if",
    "return",
    "end if",
    "end repeat",
    "end repeat",
    "end tell",
    "end run",
)


def _close_terminal(terminal_tty: str) -> int:
    """Chiude solo la scheda Terminale che possiede il TTY indicato."""

    if not terminal_tty.startswith("/dev/tty"):
        return 0

    time.sleep(0.4)
    command = ["/usr/bin/osascript"]
    for line in APPLE_SCRIPT_LINES:
        command.extend(("-e", line))
    command.append(terminal_tty)
    return subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode


def _launch_app(project_directory: Path, terminal_tty: str) -> int:
    """Avvia l'app in una nuova sessione, indipendente dalla console."""

    main_file = project_directory / "main.py"
    if not main_file.is_file():
        return 2

    log_file = Path(tempfile.gettempdir()) / "immagini-in-pdf-avvio.log"
    with log_file.open("ab", buffering=0) as log:
        subprocess.Popen(
            [sys.executable, str(main_file)],
            cwd=project_directory,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )

    if terminal_tty.startswith("/dev/tty"):
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--close", terminal_tty],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    return 0


def main(arguments: list[str]) -> int:
    if len(arguments) == 2 and arguments[0] == "--close":
        return _close_terminal(arguments[1])
    if len(arguments) != 2:
        return 2
    return _launch_app(Path(arguments[0]).resolve(), arguments[1])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
