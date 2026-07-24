#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
gf_need ghostfs-snapshot-gui "Build tools/snapshot-gui from ghostfs-kernel."
exec ghostfs-snapshot-gui "$1"
