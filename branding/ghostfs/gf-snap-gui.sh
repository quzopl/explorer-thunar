#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
gf_need ghostfs-snapshot-gui "Zbuduj tools/snapshot-gui z ghostfs-kernel."
exec ghostfs-snapshot-gui "$1"
