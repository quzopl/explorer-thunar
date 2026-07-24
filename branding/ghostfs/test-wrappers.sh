#!/usr/bin/env bash
set -u
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$PWD/dist-ghostfs:$PATH"
. "$HERE/gf-common.sh"
fail=0
# gf_is_ghostfs: a normal /tmp dir is NOT ghostfs
if gf_is_ghostfs /tmp 2>/dev/null; then echo "FAIL: /tmp reported as ghostfs"; fail=1; else echo "ok: /tmp not ghostfs"; fi
# gf-reflink on a plain-FS file: must fail loudly (no CoW), not silently copy
T=$(mktemp -d); echo x > "$T/a";
if GF_NONINTERACTIVE=1 "$HERE/gf-reflink.sh" "$T/a" 2>/dev/null; then echo "FAIL: reflink 'succeeded' on non-CoW"; fail=1; else echo "ok: reflink refused on non-CoW"; fi
rm -rf "$T"
[ "$fail" = 0 ] && echo "WRAPPERS-OK" || { echo "WRAPPERS-FAIL"; exit 1; }
