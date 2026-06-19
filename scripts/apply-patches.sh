#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d thunar-src ]; then
  echo "Brak thunar-src/ — uruchom najpierw scripts/fetch-sources.sh" >&2
  exit 1
fi
shopt -s nullglob
for p in patches/*.patch; do
  echo "Aplikuję $p"
  patch -p0 -d thunar-src < "$p"
done
echo "OK: patche zaaplikowane"
