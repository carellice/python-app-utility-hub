#!/bin/bash
cd "$(dirname "$0")"

fail() {
  osascript -e "display dialog \"$1\" buttons {\"OK\"} with icon caution" >/dev/null
  exit 1
}

if ! command -v python3 >/dev/null 2>&1; then
  fail "Python 3 non trovato. Installa Python 3.10 o superiore."
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Prima configurazione in corso..."
  python3 -m venv .venv || fail "Non riesco a creare l'ambiente Python."
  ".venv/bin/python" -m pip install --upgrade pip || fail "Non riesco ad aggiornare pip."
  ".venv/bin/python" -m pip install -r requirements.txt || fail "Non riesco a installare le dipendenze Python."
fi

if ! ".venv/bin/python" -c "import mutagen, PIL; import importlib.metadata as m; m.version('tkinterdnd2-universal')" >/dev/null 2>&1; then
  echo "Aggiornamento dipendenze in corso..."
  ".venv/bin/python" -m pip install -r requirements.txt || fail "Non riesco a installare le dipendenze Python."
fi

nohup ".venv/bin/python" "app.py" "$@" >/tmp/mp3-tag-editor.log 2>&1 < /dev/null &
APP_PID=$!
sleep 2

if ! kill -0 "$APP_PID" >/dev/null 2>&1; then
  /usr/bin/osascript -e 'display dialog "Il programma non e partito. Ho scritto i dettagli in /tmp/mp3-tag-editor.log" buttons {"OK"} with icon caution' >/dev/null
  exit 1
fi

disown "$APP_PID" 2>/dev/null || true

TERMINAL_WINDOW_ID=$(/usr/bin/osascript -e 'tell application "Terminal" to if (count of windows) > 0 then id of front window' 2>/dev/null || true)
if [ -n "$TERMINAL_WINDOW_ID" ]; then
  /usr/bin/osascript >/dev/null 2>&1 <<APPLESCRIPT
do shell script "/usr/bin/nohup /bin/sh -c " & quoted form of "sleep 1; /usr/bin/osascript -e 'tell application \"Terminal\" to if exists window id $TERMINAL_WINDOW_ID then close window id $TERMINAL_WINDOW_ID saving no' >/dev/null 2>&1" & " >/dev/null 2>&1 &"
APPLESCRIPT
fi

exit 0
