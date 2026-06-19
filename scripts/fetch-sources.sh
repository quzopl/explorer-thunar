#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
VER=4.20.8
SERIES=4.20
TARBALL="thunar-${VER}.tar.bz2"
URL="https://archive.xfce.org/src/xfce/thunar/${SERIES}/${TARBALL}"
mkdir -p .cache
if [ ! -f ".cache/${TARBALL}" ]; then
  echo "Pobieram ${URL}"
  curl -fL --retry 3 -o ".cache/${TARBALL}" "${URL}"
fi
rm -rf thunar-src
mkdir -p thunar-src
tar -xjf ".cache/${TARBALL}" -C thunar-src --strip-components=1
echo "OK: rozpakowano do thunar-src/"
