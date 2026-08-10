#!/bin/bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 non trovato. Installa Python 3.10 o superiore."
  read -r -p "Premi Invio per chiudere."
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

".venv/bin/python" -m pip install --upgrade pip
".venv/bin/python" -m pip install -r requirements.txt

chmod +x "Avvia_Mac.command"

echo
echo "Configurazione completata. Avvia il programma con Avvia_Mac.command"
read -r -p "Premi Invio per chiudere."
