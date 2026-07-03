#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d thunar-src ]; then
  echo "Brak thunar-src/ — uruchom najpierw scripts/fetch-sources.sh" >&2
  exit 1
fi
# Seria patchy jest sekwencyjna (późniejsze przepisują kod wcześniejszych),
# więc nie da się jej częściowo reaplikować. Znacznik czyni skrypt
# idempotentnym: drugie uruchomienie to no-op zamiast interaktywnego
# zawieszenia patcha na pytaniu o "Reversed patch".
STAMP=thunar-src/.explorer-patches-applied
if [ -f "$STAMP" ]; then
  echo "Patche już zaaplikowane ($STAMP) — nic do zrobienia."
  echo "Czysty stan: bash scripts/fetch-sources.sh && bash scripts/apply-patches.sh"
  exit 0
fi
shopt -s nullglob
for p in patches/*.patch; do
  echo "Aplikuję $p"
  # -N: nigdy nie pytaj interaktywnie o odwrócony patch; set -e przerwie na błędzie
  patch -p0 -N -d thunar-src < "$p"
done
touch "$STAMP"
echo "OK: patche zaaplikowane"
