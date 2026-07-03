#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX="$PWD/install"
# binarka explorer = dowiązanie do zbudowanego thunar
ln -sf thunar "$PREFIX/bin/explorer"
# plik .desktop (w prefiksie + w ~/.local/share/applications jako nazwa app-id,
# żeby KDE skojarzyło okno (app_id io.github.quzopl.Explorer) z wpisem -> pasek zadań/ikona)
# Exec generujemy z aktualnego $PREFIX — wpis działa niezależnie od tego, gdzie
# leży repo (koniec zaszytych na sztywno ścieżek typu /mnt/swiezak/...).
mkdir -p "$PREFIX/share/applications"
DESKTOP_TMP="$(mktemp)"
sed "s|^Exec=.*|Exec=$PREFIX/bin/explorer %F|" branding/explorer.desktop > "$DESKTOP_TMP"
install -m644 "$DESKTOP_TMP" "$PREFIX/share/applications/explorer.desktop"
# nazwa pliku musi odpowiadać app_id okna (GTK3/Wayland: prgname = "explorer")
USER_APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$USER_APPS"
rm -f "$USER_APPS/io.github.quzopl.Explorer.desktop"   # poprzednia, błędna nazwa
install -m644 "$DESKTOP_TMP" "$USER_APPS/explorer.desktop"
rm -f "$DESKTOP_TMP"
update-desktop-database "$USER_APPS" 2>/dev/null || true
# palety motywów (8 palet; bazowy explorer.css nie jest już używany od patcha 12)
mkdir -p "$PREFIX/share/explorer/themes"
install -m644 branding/themes/*.css "$PREFIX/share/explorer/themes/"

# ikona aplikacji (Icon=explorer w .desktop) — w prefiksie i dla użytkownika,
# żeby pasek zadań/menu miały ikonę bez zewnętrznego motywu ikon
for ICONDIR in "$PREFIX/share/icons/hicolor/scalable/apps" \
               "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"; do
  mkdir -p "$ICONDIR"
  install -m644 branding/explorer.svg "$ICONDIR/explorer.svg"
done
gtk-update-icon-cache -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" 2>/dev/null || true

# „Open Terminal Here": Thunar NIE nadpisuje istniejącego ~/.config/Thunar/uca.xml
# naszym szablonem, więc starsza konfiguracja użytkownika nadal woła stary
# `exo-open --launch TerminalEmulator` (pada, gdy exo nie ma terminala) albo
# gołe `konsole` (pada bez KDE). Zmigruj obie idempotentnie na łańcuch
# z fallbackami (konsole -> xfce4-terminal -> gnome-terminal -> ... -> xterm).
UCA="${XDG_CONFIG_HOME:-$HOME/.config}/Thunar/uca.xml"
# Bez pliku użytkownika Thunar szuka szablonu w XDG_CONFIG_DIRS (/etc/xdg),
# a nasz instaluje się do $PREFIX/etc/xdg — niewidoczny. Zasiej go, inaczej
# menu kontekstowe nie ma ŻADNYCH akcji (w tym "Open Terminal Here").
if [ ! -f "$UCA" ] && [ -f "$PREFIX/etc/xdg/Thunar/uca.xml" ]; then
  mkdir -p "$(dirname "$UCA")"
  install -m644 "$PREFIX/etc/xdg/Thunar/uca.xml" "$UCA"
  echo "OK: zasiano $UCA (akcja Open Terminal Here)"
fi
if [ -f "$UCA" ]; then
  UCA_FILE="$UCA" python3 - <<'PYEOF'
import os
uca = os.environ['UCA_FILE']
new_cmd = ('d=%f; if command -v konsole >/dev/null; then exec konsole --workdir "$d"; '
           'elif command -v xfce4-terminal >/dev/null; then exec xfce4-terminal --working-directory "$d"; '
           'elif command -v gnome-terminal >/dev/null; then exec gnome-terminal --working-directory="$d"; '
           'elif command -v x-terminal-emulator >/dev/null; then cd "$d"; exec x-terminal-emulator; '
           'else cd "$d"; exec xterm; fi')
old_cmds = ['exo-open --working-directory %f --launch TerminalEmulator',
            'konsole --workdir %f']
s = open(uca).read()
out = s
for old in old_cmds:
    out = out.replace('<command>%s</command>' % old, '<command>%s</command>' % new_cmd)
if out != s:
    import time
    open('%s.bak.%d' % (uca, time.time()), 'w').write(s)
    open(uca, 'w').write(out)
    print('OK: zmigrowano akcję terminala w %s (fallback chain)' % uca)
PYEOF
fi
echo "OK: branding zainstalowany"
