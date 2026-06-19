#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX="$PWD/install"
# binarka explorer = dowiązanie do zbudowanego thunar
ln -sf thunar "$PREFIX/bin/explorer"
# plik .desktop
mkdir -p "$PREFIX/share/applications"
install -m644 branding/explorer.desktop "$PREFIX/share/applications/explorer.desktop"
echo "OK: branding zainstalowany"
