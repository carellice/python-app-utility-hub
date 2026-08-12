#!/usr/bin/env bash
set -euo pipefail

version="${1:?Versione richiesta, ad esempio 1.0.0}"
architecture="${2:?Architettura richiesta, ad esempio arm64 oppure x64}"
app_path="${3:?Percorso applicazione .app richiesto}"
output_dir="${4:-release/installers}"
script_dir="$(cd "$(dirname "$0")" && pwd)"
component_plist="$script_dir/macos-component.plist"

mkdir -p "$output_dir"
package_root="$(mktemp -d "$output_dir/.package-root.XXXXXX")"
trap 'rm -rf "$package_root"' EXIT
mkdir -p "$package_root/Applications"
ditto "$app_path" "$package_root/Applications/Python App Utility Hub.app"

pkgbuild \
  --root "$package_root" \
  --component-plist "$component_plist" \
  --identifier "com.fc.pythonapputilityhub" \
  --version "$version" \
  --install-location "/" \
  "$output_dir/Python-App-Utility-Hub-macos-${architecture}.pkg"
