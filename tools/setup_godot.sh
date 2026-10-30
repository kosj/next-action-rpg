#!/usr/bin/env bash
set -euo pipefail
# Install only within a chosen writable tools directory. Existing global installs are untouched.
runefall_version=4.6.3
runefall_tools="${RUNEFALL_TOOLS_DIR:-/tmp/runefall-tools}"
runefall_data="${XDG_DATA_HOME:-/tmp/runefall-data}"
mkdir -p "$runefall_tools" "$runefall_data/godot/export_templates/$runefall_version.stable"
if [ ! -x "$runefall_tools/godot" ]; then
  curl --fail --location --retry 3 -o "$runefall_tools/editor.zip" "https://github.com/godotengine/godot-builds/releases/download/$runefall_version-stable/Godot_v$runefall_version-stable_linux.x86_64.zip"
  unzip -oq "$runefall_tools/editor.zip" -d "$runefall_tools"
  mv "$runefall_tools/Godot_v$runefall_version-stable_linux.x86_64" "$runefall_tools/godot"
  chmod +x "$runefall_tools/godot"
  rm "$runefall_tools/editor.zip"
fi
if [ ! -f "$runefall_data/godot/export_templates/$runefall_version.stable/web_nothreads_release.zip" ] || [ ! -f "$runefall_data/godot/export_templates/$runefall_version.stable/windows_release_x86_64.exe" ]; then
  curl --fail --location --retry 3 -o "$runefall_tools/templates.tpz" "https://github.com/godotengine/godot-builds/releases/download/$runefall_version-stable/Godot_v$runefall_version-stable_export_templates.tpz"
  unzip -ojq "$runefall_tools/templates.tpz" 'templates/web_nothreads_release.zip' 'templates/web_nothreads_debug.zip' 'templates/windows_release_x86_64.exe' 'templates/windows_debug_x86_64.exe' 'templates/version.txt' -d "$runefall_data/godot/export_templates/$runefall_version.stable"
  rm "$runefall_tools/templates.tpz"
fi
printf 'GODOT_BIN=%s/godot\nXDG_DATA_HOME=%s\n' "$runefall_tools" "$runefall_data"
