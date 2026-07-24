#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
c="$1"
name="$(basename "$c" .gfs)"
mp="${XDG_DATA_HOME:-$HOME/.local/share}/ghostfs-mounts/$name"
if findmnt -no TARGET "$mp" >/dev/null 2>&1; then
  fusermount3 -u "$mp" 2>/dev/null || fusermount -u "$mp"
  rmdir "$mp" 2>/dev/null || true
  gf_info "Odmontowano $name."
else
  gf_err "The container is not mounted."
  exit 1
fi
