#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX="$PWD/install"
cd thunar-src
# rekonfiguruj, gdy drzewo było skonfigurowane z innym prefiksem (np. /usr
# przez build-appimage.sh) — inaczej `make install` poleciałby do /usr!
if [ -f config.status ] && ! ./config.status --config | grep -qF -- "--prefix=$PREFIX"; then
  echo "config.status ma inny prefix — rekonfiguruję na $PREFIX"
  rm -f config.status
fi
if [ ! -f config.status ]; then
  ./configure --prefix="$PREFIX" --disable-static --enable-gio-unix \
    --disable-introspection
fi
make -j"$(nproc)"
make install
echo "OK: zainstalowano do $PREFIX"
