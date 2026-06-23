#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
echo "== CSS zainstalowany =="
[ -f install/share/explorer/explorer.css ] && echo "css OK" || { echo "BRAK css"; fail=1; }
echo "== start bez błędów parsowania CSS / GDK =="
timeout 8 ./install/bin/explorer "$HOME" 2>/tmp/exp-v2.err & MYPID=$!
for _ in 1 2 3 4 5; do busctl --user list 2>/dev/null | grep -q io.github.quzopl.Explorer && break; sleep 1; done
sleep 1
if grep -qi "Theme parsing error\|segfault\|GDK_IS_SCREEN\|CRITICAL.*css" /tmp/exp-v2.err; then
  echo "BŁĘDY:"; cat /tmp/exp-v2.err; fail=1
else echo "start OK"; fi
wait $MYPID 2>/dev/null
[ "$fail" = 0 ] && echo "ETAP 2: SUKCES" || echo "ETAP 2: SĄ BŁĘDY"
exit $fail
