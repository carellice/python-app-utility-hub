#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
BUILD_VENV="$SCRIPT_DIR/.venv-build"
cd "$SCRIPT_DIR"

if [[ ! -x "$BUILD_VENV/bin/python" ]]; then
  python3 -m venv "$BUILD_VENV"
fi

"$BUILD_VENV/bin/python" -m pip install -r requirements-build.txt
"$BUILD_VENV/bin/python" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "Immagini in PDF" \
  --osx-bundle-identifier "it.local.immagini-in-pdf" \
  main.py

print "Applicazione creata in: $SCRIPT_DIR/dist/Immagini in PDF.app"
