#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX="$PWD/install"
# binarka explorer = dowiązanie do zbudowanego thunar
ln -sf thunar "$PREFIX/bin/explorer"
# plik .desktop (w prefiksie + w ~/.local/share/applications jako nazwa app-id,
# żeby KDE skojarzyło okno (app_id eu.mizak.Explorer) z wpisem -> pasek zadań/ikona)
# Exec generujemy z aktualnego $PREFIX — wpis działa niezależnie od tego, gdzie
# leży repo (koniec zaszytych na sztywno ścieżek typu /mnt/swiezak/...).
mkdir -p "$PREFIX/share/applications"
DESKTOP_TMP="$(mktemp)"
sed "s|^Exec=.*|Exec=$PREFIX/bin/explorer %F|" branding/explorer.desktop > "$DESKTOP_TMP"
install -m644 "$DESKTOP_TMP" "$PREFIX/share/applications/explorer.desktop"
# nazwa pliku musi odpowiadać app_id okna (GTK3/Wayland: prgname = "explorer")
USER_APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$USER_APPS"
rm -f "$USER_APPS/eu.mizak.Explorer.desktop"   # poprzednia, błędna nazwa
install -m644 "$DESKTOP_TMP" "$USER_APPS/explorer.desktop"
rm -f "$DESKTOP_TMP"
update-desktop-database "$USER_APPS" 2>/dev/null || true
# motyw CSS Win11 + palety motywów
mkdir -p "$PREFIX/share/explorer/themes"
install -m644 branding/explorer.css "$PREFIX/share/explorer/explorer.css"
install -m644 branding/themes/*.css "$PREFIX/share/explorer/themes/"
echo "OK: branding zainstalowany"
