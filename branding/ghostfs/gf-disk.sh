#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
gf_need ghostfs-disk-tool "Build tools/disk-tool from ghostfs-kernel."
exec ghostfs-disk-tool "$1"
