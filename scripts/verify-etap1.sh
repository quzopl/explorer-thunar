#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
echo "== 1. binar explorer istnieje i ma wersję =="
timeout 5 ./install/bin/explorer --version | head -1 || fail=1
echo "== 2. systemowy thunar nietknięty =="
/usr/bin/thunar --version | head -1 || fail=1
echo "== 3. osobny app-id na magistrali =="
timeout 9 ./install/bin/explorer /tmp >/dev/null 2>&1 &
MYPID=$!
found=0
for _ in 1 2 3 4 5 6 7; do
  if busctl --user list 2>/dev/null | grep -q "eu.mizak.Explorer"; then found=1; break; fi
  kill -0 $MYPID 2>/dev/null || break
  sleep 1
done
if [ "$found" = 1 ]; then echo "app-id OK"; else echo "BRAK app-id"; fail=1; fi
echo "== 4. osobny kanał xfconf =="
xfconf-query -c explorer -l >/dev/null 2>&1 && echo "kanal OK" || echo "(kanal jeszcze pusty — OK jeśli brak zapisów)"
wait $MYPID 2>/dev/null
[ "$fail" = 0 ] && echo "ETAP 1: SUKCES" || echo "ETAP 1: SĄ BŁĘDY"
exit $fail
