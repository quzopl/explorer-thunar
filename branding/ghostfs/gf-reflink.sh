#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
f="$1"
dst="$(dirname "$f")/$(basename "$f") (reflink)"
if cp --reflink=always -- "$f" "$dst" 2>/dev/null; then
  [ "${GF_NONINTERACTIVE:-}" = 1 ] || gf_info "Created reflink: $(basename "$dst")"
else
  gf_err "Reflink not available — the file is not on a ghostfs/CoW volume."
  exit 1
fi
