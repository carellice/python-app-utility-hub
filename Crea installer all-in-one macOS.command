#!/usr/bin/env bash
# Pubblica una release GitHub che genera Windows, macOS Intel e macOS Apple Silicon.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

finish_with_error() {
  status=$?
  if [[ "$status" -ne 0 ]]; then
    printf "\nLa creazione della release non è riuscita (codice %s).\n" "$status"
    read -r -n 1 -s -p "Premi un tasto per chiudere…" || true
  fi
  exit "$status"
}
trap finish_with_error EXIT

printf '╔══════════════════════════════════════════════════════╗\n'
printf '║ Python App Utility Hub — release universale GitHub  ║\n'
printf '╚══════════════════════════════════════════════════════╝\n\n'
printf 'Questa procedura creerà automaticamente gli installer:\n'
printf '  • Windows x64 (.exe)\n  • macOS Intel (.pkg)\n  • macOS Apple Silicon (.pkg)\n\n'
read -r -p 'Versione della release [1.0.0]: ' RELEASE_VERSION
RELEASE_VERSION="${RELEASE_VERSION:-1.0.0}"
RELEASE_TAG="v${RELEASE_VERSION#v}"

if [[ ! "$RELEASE_TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  printf 'La versione deve avere il formato 1.0.0.\n'
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  printf 'Git non è installato. Installa gli strumenti Xcode e riapri questo file.\n'
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  printf 'Ci sono modifiche non salvate in Git. Esegui prima un commit e riapri questo file.\n'
  exit 1
fi
if [[ "$(git branch --show-current)" != "main" ]]; then
  printf 'Per pubblicare una release devi trovarti sul branch main.\n'
  exit 1
fi
if ! git remote get-url origin >/dev/null 2>&1; then
  printf 'Non trovo il remoto GitHub "origin".\n'
  exit 1
fi
if git rev-parse -q --verify "refs/tags/$RELEASE_TAG" >/dev/null; then
  printf 'Il tag locale %s esiste già: scegli un’altra versione.\n' "$RELEASE_TAG"
  exit 1
fi
if [[ -n "$(git ls-remote --tags origin "refs/tags/$RELEASE_TAG")" ]]; then
  printf 'Il tag %s esiste già su GitHub: scegli un’altra versione.\n' "$RELEASE_TAG"
  exit 1
fi

printf '\nVerranno pubblicati il branch main e il tag %s su GitHub.\n' "$RELEASE_TAG"
read -r -p 'Continuare? [s/N]: ' CONFIRMATION
if [[ ! "$CONFIRMATION" =~ ^[sS]$ ]]; then
  printf 'Operazione annullata.\n'
  trap - EXIT
  read -r -n 1 -s -p 'Premi un tasto per chiudere…' || true
  exit 0
fi

printf '\nPubblico il codice necessario…\n'
git push origin main
git tag -a "$RELEASE_TAG" -m "Release $RELEASE_TAG"
git push origin "$RELEASE_TAG"

REMOTE_URL="$(git remote get-url origin)"
case "$REMOTE_URL" in
  https://github.com/*)
    REPOSITORY_URL="${REMOTE_URL%.git}"
    ;;
  git@github.com:*)
    REPOSITORY_URL="https://github.com/${REMOTE_URL#git@github.com:}"
    REPOSITORY_URL="${REPOSITORY_URL%.git}"
    ;;
  *)
    REPOSITORY_URL=""
    ;;
esac

printf '\nRelease avviata su GitHub. I tre installer saranno disponibili tra alcuni minuti.\n'
if [[ -n "$REPOSITORY_URL" && "${UTILITY_HUB_NO_OPEN:-}" != "1" ]]; then
  open "$REPOSITORY_URL/actions"
fi

trap - EXIT
read -r -n 1 -s -p 'Premi un tasto per chiudere…' || true
printf '\n'
