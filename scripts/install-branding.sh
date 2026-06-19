#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX="$PWD/install"
# binarka explorer = dowiązanie do zbudowanego thunar
ln -sf thunar "$PREFIX/bin/explorer"
# plik .desktop
mkdir -p "$PREFIX/share/applications"
install -m644 branding/explorer.desktop "$PREFIX/share/applications/explorer.desktop"
# motyw CSS Win11 + palety motywów
mkdir -p "$PREFIX/share/explorer/themes"
install -m644 branding/explorer.css "$PREFIX/share/explorer/explorer.css"
install -m644 branding/themes/*.css "$PREFIX/share/explorer/themes/"
echo "OK: branding zainstalowany"
