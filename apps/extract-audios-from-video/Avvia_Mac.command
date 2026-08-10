#!/bin/zsh
SCRIPT_DIR="${0:A:h}"
LOG_FILE="${TMPDIR:-/tmp}/extract-audio-tracks.log"

cd "$SCRIPT_DIR" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display alert "Python 3 non trovato" message "Installa Python 3 e riprova."'
  exit 1
fi

nohup python3 "$SCRIPT_DIR/extract_audio_tracks.py" >"$LOG_FILE" 2>&1 &

osascript >/dev/null 2>&1 <<'APPLESCRIPT' &
delay 0.4
tell application "Terminal"
  if (count of windows) > 0 then
    close front window saving no
  end if
end tell
APPLESCRIPT

exit 0
