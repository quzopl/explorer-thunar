#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX="$PWD/install"
cd thunar-src
# rekonfiguruj, gdy drzewo było skonfigurowane z innym prefiksem (np. /usr
# przez build-appimage.sh) — inaczej `make install` poleciałby do /usr!
if [ -f config.status ] && ! ./config.status --config | grep -qF -- "--prefix=$PREFIX"; then
  echo "config.status ma inny prefix — rekonfiguruję na $PREFIX"
  # clean PRZED usunięciem config.status (bez niego make clean nie działa),
  # inaczej przeżywają obiekty z zapieczonymi ścieżkami starego prefiksu
  # (DATADIR, THUNARX_DIRECTORY -> np. martwe wtyczki UCA)
  make clean >/dev/null 2>&1 || true
  rm -f config.status
fi
if [ ! -f config.status ]; then
  ./configure --prefix="$PREFIX" --disable-static --enable-gio-unix \
    --disable-introspection
fi
# wersja aplikacji (menu Help -> Check for Updates) z tagu gita
EXPLORER_VERSION="${EXPLORER_VERSION_OVERRIDE:-$(git -C .. describe --tags --abbrev=0 2>/dev/null || echo dev)}"
make -j"$(nproc)" CPPFLAGS="-DEXPLORER_VERSION='\"$EXPLORER_VERSION\"'"
make install
echo "OK: zainstalowano do $PREFIX"
