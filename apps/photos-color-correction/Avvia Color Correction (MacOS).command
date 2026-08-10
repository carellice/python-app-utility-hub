#!/bin/bash

cd "$(dirname "$0")" || exit 1

PROJECT_DIR="$(pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
GUI_LOG="$PROJECT_DIR/gui.log"

if command -v python3 >/dev/null 2>&1; then
  BASE_PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  BASE_PYTHON="python"
else
  echo "Python non trovato. Installa Python 3.10 o superiore da https://www.python.org/downloads/"
  read -r -p "Premi Invio per chiudere..."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creo l'ambiente locale..."
  "$BASE_PYTHON" -m venv .venv || {
    echo "Impossibile creare l'ambiente locale."
    read -r -p "Premi Invio per chiudere..."
    exit 1
  }
fi

"$VENV_PYTHON" -c "import PIL" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Installo le dipendenze..."
  "$VENV_PYTHON" -m pip install -r requirements.txt || {
    echo "Impossibile installare le dipendenze."
    read -r -p "Premi Invio per chiudere..."
    exit 1
  }
fi

echo "Avvio l'interfaccia grafica..."
nohup "$VENV_PYTHON" "$PROJECT_DIR/gui_app.py" > "$GUI_LOG" 2>&1 &
disown

if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
  CURRENT_TTY="$(tty)"
  (
    sleep 0.7
    /usr/bin/osascript \
      -e 'tell application "Terminal"' \
      -e "close (first window whose selected tab's tty is \"$CURRENT_TTY\")" \
      -e 'end tell' >/dev/null 2>&1
  ) &
fi

exit 0
