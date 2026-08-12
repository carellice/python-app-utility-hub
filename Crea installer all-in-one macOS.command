#!/usr/bin/env bash
# Genera, con un doppio clic, l'installer .pkg adatto a questo Mac.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_ENV="$PROJECT_DIR/.release-venv"
cd "$PROJECT_DIR"

finish_with_error() {
  status=$?
  if [[ "$status" -ne 0 ]]; then
    printf "\nLa creazione dell'installer non è riuscita (codice %s).\n" "$status"
    read -r -n 1 -s -p "Premi un tasto per chiudere…" || true
  fi
  exit "$status"
}
trap finish_with_error EXIT

printf '╔══════════════════════════════════════════════╗\n'
printf '║  Python App Utility Hub — generatore macOS  ║\n'
printf '╚══════════════════════════════════════════════╝\n\n'
read -r -p 'Versione della release [1.0.0]: ' RELEASE_VERSION
RELEASE_VERSION="${RELEASE_VERSION:-1.0.0}"

PYTHON_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  printf '\nServe Python 3.10 o successivo per creare un installer.\n'
  printf 'Installa Python da https://www.python.org/downloads/ e riapri questo file.\n'
  exit 1
fi

case "$(uname -m)" in
  arm64) ARCHITECTURE="arm64" ;;
  x86_64) ARCHITECTURE="x64" ;;
  *)
    printf 'Architettura macOS non supportata: %s\n' "$(uname -m)"
    exit 1
    ;;
esac

printf "\nPreparo l'ambiente di build…\n"
if [[ ! -x "$BUILD_ENV/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$BUILD_ENV"
fi
"$BUILD_ENV/bin/python" -m pip install --upgrade pip -r requirements-build.txt

printf '\nScarico FFmpeg e FFprobe da includere…\n'
"$BUILD_ENV/bin/python" packaging/fetch_ffmpeg.py --output packaging/vendor

printf "\nCreo l'app autosufficiente…\n"
"$BUILD_ENV/bin/python" packaging/build.py --output release/app
"$BUILD_ENV/bin/python" packaging/verify_bundle.py --bundle "release/app/Python App Utility Hub.app"

printf '\nCreo il pacchetto di installazione…\n'
bash packaging/macos-installer.sh "$RELEASE_VERSION" "$ARCHITECTURE" \
  "release/app/Python App Utility Hub.app" release/installers

INSTALLER="$PROJECT_DIR/release/installers/Python-App-Utility-Hub-macos-${ARCHITECTURE}.pkg"
printf '\nInstaller creato con successo:\n%s\n' "$INSTALLER"
if [[ "${UTILITY_HUB_NO_REVEAL:-}" != "1" ]]; then
  open -R "$INSTALLER"
fi

trap - EXIT
read -r -n 1 -s -p 'Premi un tasto per chiudere…' || true
printf '\n'
