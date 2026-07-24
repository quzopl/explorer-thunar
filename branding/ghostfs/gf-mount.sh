#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
gf_need ghostfs "Zainstaluj/zbuduj ghostfs (sterownik FUSE)."
c="$1"
name="$(basename "$c" .gfs)"
mp="${XDG_DATA_HOME:-$HOME/.local/share}/ghostfs-mounts/$name"
if findmnt -no TARGET "$mp" >/dev/null 2>&1; then gf_open "$mp"; exit 0; fi
mkdir -p "$mp"
if ghostfs "$c" "$mp"; then gf_open "$mp"; else gf_err "Montowanie FUSE nie powiodło się."; rmdir "$mp" 2>/dev/null || true; exit 1; fi
