#!/usr/bin/env python3
"""Scarica FFmpeg e FFprobe statici per la piattaforma della build.

Le utility audio/video usano entrambi gli eseguibili. Tenerli nel pacchetto
evita che chi installa l'hub debba configurare manualmente un PATH di sistema.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import ssl
import stat
import urllib.request
from pathlib import Path

import certifi

RELEASE_TAG = "b6.1.2-rc.1"
RELEASE_BASE_URL = (
    "https://github.com/descriptinc/ffmpeg-ffprobe-static/releases/download/"
    f"{RELEASE_TAG}"
)


def release_platform() -> tuple[str, str, str]:
    """Mappa il sistema della build ai nomi degli asset FFmpeg fissati."""
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Windows" and machine in {"amd64", "x86_64"}:
        return "win32", "x64", ".exe"
    if system == "Darwin" and machine in {"x86_64", "amd64"}:
        return "darwin", "x64", ""
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "darwin", "arm64", ""
    raise RuntimeError(
        f"Piattaforma non supportata per la release: {system} ({platform.machine()})."
    )


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Python-App-Utility-Hub-builder"})
    # Usa il bundle CA aggiornato anche sulle installazioni Python locali che
    # non ereditano correttamente i certificati dal portachiavi del sistema.
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, context=context) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_platform, architecture, extension = release_platform()
    args.output.mkdir(parents=True, exist_ok=True)

    for tool in ("ffmpeg", "ffprobe"):
        source_name = f"{tool}-{source_platform}-{architecture}"
        destination = args.output / f"{tool}{extension}"
        url = f"{RELEASE_BASE_URL}/{source_name}"
        print(f"Scarico {source_name}…")
        download(url, destination)
        if os.name != "nt":
            destination.chmod(destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    (args.output / "FFMPEG-NOTICE.txt").write_text(
        "Python App Utility Hub include FFmpeg e FFprobe per le utility audio e video.\n\n"
        "Build di origine: descriptinc/ffmpeg-ffprobe-static, release "
        f"{RELEASE_TAG}.\n"
        f"Asset: {RELEASE_BASE_URL}\n\n"
        "FFmpeg e le sue librerie sono distribuiti secondo le rispettive licenze. "
        "Consulta https://ffmpeg.org/legal.html e il repository dell'asset per "
        "le condizioni complete e il codice sorgente corrispondente.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
