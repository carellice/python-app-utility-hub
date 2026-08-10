#!/bin/zsh
setopt null_glob
cd "${0:A:h}" || exit 1

for candidate in \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/*/bin/python3 \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    /usr/bin/python3
do
    if [ -x "$candidate" ] && "$candidate" -c 'import tkinter, PIL' >/dev/null 2>&1; then
        "$candidate" app.py >/dev/null 2>&1 &!
        if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
            tty_path="$(tty)"
            (
                sleep 0.8
                /usr/bin/osascript -e "tell application \"Terminal\" to close (first window whose selected tab's tty is \"$tty_path\")" >/dev/null 2>&1 || \
                    /usr/bin/osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1
            ) >/dev/null 2>&1 &!
        fi
        exit 0
    fi
done

/usr/bin/osascript -e 'display dialog "Non trovo una versione di Python con Tkinter e Pillow. Apri il README per le istruzioni di installazione." buttons {"OK"} default button "OK" with icon caution'
exit 1
