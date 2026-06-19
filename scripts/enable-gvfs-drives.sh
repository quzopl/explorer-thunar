#!/usr/bin/env bash
# Dopisuje x-gvfs-show do wpisów /mnt/* w /etc/fstab, by wszystkie dyski
# pokazywały się w panelu "Nośniki" (Explorer/Thunar/Nautilus).
# Uruchom przez: sudo bash scripts/enable-gvfs-drives.sh
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Uruchom przez sudo." >&2; exit 1; }

BACKUP="/etc/fstab.bak.$(date +%Y%m%d-%H%M%S)"
cp /etc/fstab "$BACKUP"
echo "Backup: $BACKUP"

awk '{
  if ($1 !~ /^#/ && $2 ~ /^\/mnt\// && $0 !~ /x-gvfs-show/ && $4 != "") {
    $4 = $4 ",x-gvfs-show"
  }
  print
}' OFS="\t" /etc/fstab > /etc/fstab.tmp

# walidacja: liczba wierszy musi się zgadzać
if [ "$(wc -l < /etc/fstab)" != "$(wc -l < /etc/fstab.tmp)" ]; then
  echo "BŁĄD: różna liczba wierszy, przerywam." >&2; rm -f /etc/fstab.tmp; exit 1
fi
mv /etc/fstab.tmp /etc/fstab
systemctl daemon-reload || true
echo "OK: x-gvfs-show dodane. Zrestartuj Explorer (i ewentualnie wyloguj/zaloguj),"
echo "    aby dyski pojawiły się w Nośnikach."
