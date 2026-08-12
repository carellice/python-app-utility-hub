#!/usr/bin/env bash
set -euo pipefail

version="${1:?Versione richiesta, ad esempio 1.0.0}"
architecture="${2:?Architettura richiesta, ad esempio arm64 oppure x64}"
app_path="${3:?Percorso applicazione .app richiesto}"
output_dir="${4:-release/installers}"

mkdir -p "$output_dir"
pkgbuild \
  --component "$app_path" \
  --identifier "com.fc.pythonapputilityhub" \
  --version "$version" \
  --install-location "/Applications" \
  "$output_dir/Python-App-Utility-Hub-macos-${architecture}.pkg"
