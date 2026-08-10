#!/bin/zsh

# Finder apre necessariamente i file .command in Terminale. Questo script usa
# un launcher Python separato, che avvia la GUI e richiude subito la sola scheda
# Terminale impiegata per il doppio clic.

SCRIPT_DIR="${0:A:h}"
START_TTY="$(tty 2>/dev/null)"

if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif [[ -x "$SCRIPT_DIR/.venv-build/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv-build/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  osascript -e 'display dialog "Python 3 non è installato. Installalo da python.org e riprova." with title "Immagini in PDF" buttons {"OK"} default button "OK" with icon stop'
  osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1
  exit 1
fi

if ! "$PYTHON_BIN" -c 'import tkinter; import PIL' >/dev/null 2>&1; then
  osascript -e 'display dialog "Mancano Tkinter o Pillow. Apri Terminale nella cartella del programma ed esegui: python3 -m pip install -r requirements.txt" with title "Immagini in PDF" buttons {"OK"} default button "OK" with icon caution'
  "$PYTHON_BIN" "$SCRIPT_DIR/image_to_pdfs/launcher.py" --close "$START_TTY" >/dev/null 2>&1
  exit 1
fi

cd "$SCRIPT_DIR" || exit 1
"$PYTHON_BIN" "$SCRIPT_DIR/image_to_pdfs/launcher.py" "$SCRIPT_DIR" "$START_TTY"
exit $?
