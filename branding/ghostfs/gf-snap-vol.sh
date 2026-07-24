#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
gf_need ghostfs-snapshot-gui "Zbuduj tools/snapshot-gui z ghostfs-kernel."
if ! gf_is_ghostfs "$1"; then gf_err "To nie jest wolumen ghostfs."; exit 1; fi
mp="$(gf_mountpoint "$1")"
exec ghostfs-snapshot-gui "$mp"
