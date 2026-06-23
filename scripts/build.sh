#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX="$PWD/install"
cd thunar-src
if [ ! -f config.status ]; then
  ./configure --prefix="$PREFIX" --disable-static --enable-gio-unix \
    --disable-introspection
fi
make -j"$(nproc)"
make install
echo "OK: zainstalowano do $PREFIX"
