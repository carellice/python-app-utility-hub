#!/usr/bin/env python3
"""Controlla la struttura di una release PyInstaller senza avviarne la GUI."""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path


UTILITY_PROGRAMS = (
    ("comic-tag-editor", "comic_tag_editor.py"),
    ("mp3-tag-editor", "app.py"),
    ("photos-color-correction", "gui_app.py"),
    ("similar-photos", "app.py"),
    ("images-to-pdfs", "main.py"),
    ("extract-audios-from-video", "extract_audio_tracks.py"),
    ("video-track-and-sub-editor", "main.py"),
)


def data_root(bundle: Path) -> Path:
    if platform.system() == "Darwin":
        return bundle / "Contents" / "Resources"
    internal = bundle / "_internal"
    return internal if internal.is_dir() else bundle


def tools_root(bundle: Path, data: Path) -> Path:
    if platform.system() == "Darwin":
        return bundle / "Contents" / "Frameworks" / "tools"
    return data / "tools"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    data = data_root(bundle)
    tools = tools_root(bundle, data)
    extension = ".exe" if platform.system() == "Windows" else ""
    required = [
        *(data / "apps" / folder / program for folder, program in UTILITY_PROGRAMS),
        *(data / "apps" / folder / "logo.png" for folder, _ in UTILITY_PROGRAMS),
        data / "assets" / "python-app-utility-hub-logo.png",
        tools / f"ffmpeg{extension}",
        tools / f"ffprobe{extension}",
        data / "tools" / "FFMPEG-NOTICE.txt",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print("File mancanti nella release:", *missing, sep="\n", file=sys.stderr)
        return 1

    print(f"Release verificata: {bundle.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
