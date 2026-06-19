#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
echo "== patche obecne =="
[ -f patches/07-search-box.patch ] && [ -f patches/08-toolbar-items-default.patch ] && echo "patche OK" || { echo "BRAK patchy"; fail=1; }
echo "== binarka zawiera pole wyszukiwania =="
strings install/bin/thunar | grep "explorer-search" >/dev/null && echo "kod OK" || { echo "BRAK kodu"; fail=1; }
echo "== domyślna lista paska zawiera explorer-search =="
strings install/bin/thunar | grep "explorer-search:1" >/dev/null && echo "lista OK" || { echo "BRAK na liście"; fail=1; }
echo "== start bez błędów krytycznych =="
timeout 7 ./install/bin/explorer "$HOME" 2>/tmp/exp-v3.err & MYPID=$!
for _ in 1 2 3 4 5; do busctl --user list 2>/dev/null | grep -q eu.mizak.Explorer && break; sleep 1; done
sleep 1
grep -qi "segfault\|CRITICAL.*search" /tmp/exp-v3.err && { echo "BŁĘDY"; fail=1; } || echo "start OK"
wait $MYPID 2>/dev/null
[ "$fail" = 0 ] && echo "ETAP 3: SUKCES" || echo "ETAP 3: SĄ BŁĘDY"
exit $fail
