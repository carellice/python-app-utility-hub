#!/bin/zsh

unsetopt BG_NICE 2>/dev/null || true
set -e

APP_DIR="${0:A:h}"
VENV_DIR="$APP_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"

cd "$APP_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 non è installato o non è disponibile nel PATH."
  echo "Installa Python 3, poi riapri questo file."
  read -r "?Premi Invio per chiudere..."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creo l'ambiente Python locale..."
  python3 -m venv "$VENV_DIR"
fi

if ! "$PYTHON_BIN" -c "import pypdf; import PIL" >/dev/null 2>&1; then
  echo "Installo le dipendenze necessarie..."
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r requirements.txt
fi

LOG_FILE="$APP_DIR/comic_tag_editor.log"

echo "Avvio Comic Tag Editor..."
"$PYTHON_BIN" "$APP_DIR/comic_tag_editor.py" > "$LOG_FILE" 2>&1 &
disown >/dev/null 2>&1 || true

if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
  osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1 &
fi

exit 0
