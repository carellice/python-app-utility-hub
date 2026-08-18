#!/usr/bin/env python3
"""Crea un bundle desktop autosufficiente con PyInstaller.

Il risultato contiene l'interprete Python, le dipendenze, le utility e gli
strumenti FFmpeg. Deve essere eseguito sullo stesso sistema di destinazione.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Python App Utility Hub"
ICON_SOURCE = ROOT / "assets" / "python-app-utility-hub-logo.png"
VENDOR_TOOLS = ROOT / "packaging" / "vendor"

# Le utility vengono copiate nel bundle come sorgenti e avviate con runpy.  Per
# questo PyInstaller non può analizzarne gli import in modo automatico: senza
# questi moduli la finestra dell'hub si apre, ma l'app selezionata termina subito
# (per esempio con ``ModuleNotFoundError: queue``).  Gli import di terze parti
# sono raccolti più sotto con ``--collect-all``; questa lista copre quelli della
# libreria standard e i sotto-moduli tkinter caricati dalle utility.
DYNAMIC_UTILITY_IMPORTS = (
    "argparse",
    "base64",
    "collections",
    "dataclasses",
    "enum",
    "hashlib",
    "io",
    "json",
    "math",
    "os",
    "pathlib",
    "platform",
    "queue",
    "re",
    "shutil",
    "subprocess",
    "sys",
    "tempfile",
    "threading",
    "time",
    "tkinter",
    "tkinter.filedialog",
    "tkinter.scrolledtext",
    "tkinter.ttk",
    "types",
    "typing",
    "uuid",
    "zipfile",
)


def create_icon(output: Path) -> Path:
    """Genera l'icona nel formato richiesto dalla piattaforma di build."""
    image = Image.open(ICON_SOURCE).convert("RGBA")
    if platform.system() == "Windows":
        destination = output / "python-app-utility-hub.ico"
        image.save(destination, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        return destination

    destination = output / "python-app-utility-hub.icns"
    # Pillow crea direttamente un ICNS completo e evita differenze tra le
    # versioni di `iconutil` presenti sui runner macOS.
    image.save(
        destination,
        format="ICNS",
        sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)],
    )
    return destination


def tool_paths() -> tuple[Path, Path]:
    extension = ".exe" if platform.system() == "Windows" else ""
    ffmpeg = VENDOR_TOOLS / f"ffmpeg{extension}"
    ffprobe = VENDOR_TOOLS / f"ffprobe{extension}"
    missing = [str(path) for path in (ffmpeg, ffprobe) if not path.is_file()]
    if missing:
        raise RuntimeError(
            "Strumenti multimediali mancanti. Esegui prima: "
            "python packaging/fetch_ffmpeg.py --output packaging/vendor\n"
            + "\n".join(missing)
        )
    return ffmpeg, ffprobe


def stage_project_data(work: Path) -> tuple[Path, Path]:
    """Prepara solo i sorgenti necessari, senza ambienti virtuali annidati."""
    resources = work / "resources"
    ignored = shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", ".DS_Store", "._*")
    apps = resources / "apps"
    assets = resources / "assets"
    shutil.copytree(ROOT / "apps", apps, ignore=ignored)
    shutil.copytree(ROOT / "assets", assets, ignore=ignored)
    return apps, assets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "release" / "app")
    parser.add_argument("--codesign-identity", default="")
    args = parser.parse_args()

    output = args.output.resolve()
    work = ROOT / "release" / "build-work"
    shutil.rmtree(output, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    ffmpeg, ffprobe = tool_paths()
    icon = create_icon(work)
    staged_apps, staged_assets = stage_project_data(work)
    separator = os.pathsep
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(output),
        "--workpath",
        str(work / "pyinstaller"),
        "--specpath",
        str(work / "spec"),
        "--icon",
        str(icon),
        "--add-data",
        f"{staged_apps}{separator}apps",
        "--add-data",
        f"{staged_assets}{separator}assets",
        "--add-data",
        f"{ROOT / 'LICENSE'}{separator}.",
        "--add-binary",
        f"{ffmpeg}{separator}tools",
        "--add-binary",
        f"{ffprobe}{separator}tools",
        "--add-data",
        f"{VENDOR_TOOLS / 'FFMPEG-NOTICE.txt'}{separator}tools",
        "--collect-all",
        "PIL",
        "--collect-all",
        "mutagen",
        "--collect-all",
        "pypdf",
        "--collect-all",
        "tkinterdnd2",
        str(ROOT / "utility_launcher.py"),
    ]
    for module in DYNAMIC_UTILITY_IMPORTS:
        command.extend(["--hidden-import", module])
    if platform.system() == "Darwin":
        # L'hub non gestisce l'apertura di documenti o URL. argv emulation non
        # serve e interferisce con l'avvio di una utility come processo figlio.
        command.extend(["--osx-bundle-identifier", "com.fc.pythonapputilityhub"])
        if args.codesign_identity:
            command.extend(["--codesign-identity", args.codesign_identity])

    environment = os.environ.copy()
    # Non dipendere da una cache globale dell'utente: questo evita permessi
    # incoerenti su macOS e rende ripetibili le build locali e in CI.
    environment["PYINSTALLER_CONFIG_DIR"] = str(work / "pyinstaller-config")
    subprocess.run(command, cwd=ROOT, env=environment, check=True)


if __name__ == "__main__":
    main()
