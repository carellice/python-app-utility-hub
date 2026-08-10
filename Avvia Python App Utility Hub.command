#!/bin/zsh

set -e

SCRIPT_DIR="${0:A:h}"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
LOG_FILE="${TMPDIR:-/tmp}/python-app-utility-hub.log"

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "Python 3 non è installato. Installalo e riapri Python App Utility Hub." buttons {"OK"} with icon caution'
  exit 1
fi

cd "$SCRIPT_DIR"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Creo l'ambiente Python condiviso…"
  python3 -m venv "$VENV_DIR"
fi

if ! "$PYTHON_BIN" -c 'import PIL, mutagen, pypdf, tkinterdnd2' >/dev/null 2>&1; then
  echo "Installo le dipendenze necessarie…"
  if ! "$PYTHON_BIN" -m pip install -r "$SCRIPT_DIR/requirements.txt"; then
    osascript -e 'display dialog "Non riesco a installare le dipendenze. Controlla la connessione e riprova." buttons {"OK"} with icon caution'
    exit 1
  fi
fi

nohup "$PYTHON_BIN" "$SCRIPT_DIR/utility_launcher.py" >"$LOG_FILE" 2>&1 < /dev/null &
disown >/dev/null 2>&1 || true

if [[ "$TERM_PROGRAM" == "Apple_Terminal" ]]; then
  osascript -e 'tell application "Terminal" to close front window saving no' >/dev/null 2>&1 &
fi

exit 0
