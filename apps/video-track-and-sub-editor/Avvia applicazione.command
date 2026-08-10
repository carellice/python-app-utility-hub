#!/bin/zsh
SCRIPT_DIR=${0:A:h}
cd "$SCRIPT_DIR" || exit 1

# Avvia la GUI come processo indipendente: la finestra Terminale aperta dai file
# .command può così richiudersi senza terminare l'applicazione.
PYTHON_BIN=$(command -v python3)
LOG_FILE="${TMPDIR:-/tmp}/video-track-subtitle-editor.log"
PYTHON_PREFIX=$("$PYTHON_BIN" -c 'import sys; print(sys.prefix)' 2>/dev/null)
PYTHON_APP="$PYTHON_PREFIX/Resources/Python.app"

# Le installazioni Python ufficiali per macOS includono Python.app. Avviarla con
# Launch Services separa davvero la GUI dal Terminale e ne evita la chiusura
# accidentale quando la console sparisce.
if [[ -d "$PYTHON_APP" ]] && open -n -a "$PYTHON_APP" --args "$SCRIPT_DIR/main.py"; then
    :
else
    nohup "$PYTHON_BIN" "$SCRIPT_DIR/main.py" </dev/null >"$LOG_FILE" 2>&1 &
    disown
fi

# Un file .command viene normalmente aperto da Terminale.app. Lo script è già
# terminato quando parte questa richiesta, quindi non compare alcun avviso.
if [[ "$TERM_PROGRAM" == "Apple_Terminal" ]]; then
    (sleep 0.35; osascript -e 'tell application "Terminal" to if (count of windows) > 0 then close front window') >/dev/null 2>&1 &
fi

exit 0
