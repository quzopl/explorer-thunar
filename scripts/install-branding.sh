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
# palety motywów (10 palet; bazowy explorer.css nie jest już używany od patcha 12)
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

# narzędzia ghostfs: owijki + (jeśli zbudowane) binarki userspace do install/bin
mkdir -p "$PREFIX/bin"
install -m755 branding/ghostfs/gf-*.sh "$PREFIX/bin/" 2>/dev/null || true
install -m644 branding/ghostfs/gf-common.sh "$PREFIX/bin/" 2>/dev/null || true
if [ -d dist-ghostfs ]; then
  for b in ghostfs-cli ghostfs ghostfs-snapshot-gui ghostfs-disk-tool; do
    [ -x "dist-ghostfs/$b" ] && install -m755 "dist-ghostfs/$b" "$PREFIX/bin/"
  done
fi

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

# akcja "Open in Terminal" (uruchom plik w terminalu) — dołóż, jeśli brak
run_cmd = ('f=%f; export f; RUN=\'cd "$(dirname "$f")"; if [ -x "$f" ]; then "$f"; else sh "$f"; fi; s=$?; echo; '
           'echo "[process exited with code $s] press Enter to close"; read _\'; '
           'if command -v konsole >/dev/null; then exec konsole -e sh -c "$RUN"; '
           'elif command -v xfce4-terminal >/dev/null; then exec xfce4-terminal -x sh -c "$RUN"; '
           'elif command -v gnome-terminal >/dev/null; then exec gnome-terminal -- sh -c "$RUN"; '
           'elif command -v x-terminal-emulator >/dev/null; then exec x-terminal-emulator -e sh -c "$RUN"; '
           'else exec xterm -e sh -c "$RUN"; fi')
if '<name>Open in Terminal</name>' not in out and '</actions>' in out:
    action = ('  <action>\n    <icon>utilities-terminal</icon>\n    <patterns>*</patterns>\n'
              '    <name>Open in Terminal</name>\n    <command>%s</command>\n'
              '    <description>Run the selected file in a terminal window</description>\n'
              '    <startup-notify/>\n    <text-files/>\n    <other-files/>\n  </action>\n\n</actions>' % run_cmd)
    out = out.replace('</actions>', action)

gf_actions = '''  <action>
    <icon>drive-harddisk</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Mount (FUSE)</name>
    <command>gf-mount.sh %f</command>
    <description>Mount a ghostfs container via FUSE</description>
    <startup-notify/>
    <other-files/>
  </action>
  <action>
    <icon>media-eject</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Unmount</name>
    <command>gf-umount.sh %f</command>
    <description>Unmount the ghostfs volume</description>
    <other-files/>
  </action>
  <action>
    <icon>document-open-recent</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Snapshots…</name>
    <command>gf-snap-gui.sh %f</command>
    <description>Manage snapshots of the ghostfs container</description>
    <other-files/>
  </action>
  <action>
    <icon>drive-removable-media</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Format / manage</name>
    <command>gf-disk.sh %f</command>
    <description>Format/manage the ghostfs volume (disk-tool)</description>
    <other-files/>
  </action>
  <action>
    <icon>document-open-recent</icon>
    <patterns>*</patterns>
    <name>ghostfs: Snapshots of this volume…</name>
    <command>gf-snap-vol.sh %f</command>
    <description>Snapshots of the mounted ghostfs volume</description>
    <directories/>
  </action>
  <action>
    <icon>edit-copy</icon>
    <patterns>*</patterns>
    <name>ghostfs: Copy as reflink</name>
    <command>gf-reflink.sh %f</command>
    <description>CoW clone (reflink) within the ghostfs volume</description>
    <other-files/>
    <text-files/>
    <image-files/>
    <audio-files/>
    <video-files/>
  </action>
'''
import re
# usuń istniejące akcje ghostfs (PL lub EN) rozpoznane po komendzie gf-*.sh,
# potem wstaw aktualny angielski zestaw — zapobiega duplikatom po migracji z v1.3.x
out = re.sub(r'[ \t]*<action>(?:(?!</action>).)*?<command>gf-[^<]*</command>(?:(?!</action>).)*?</action>\n?',
             '', out, flags=re.S)
if '</actions>' in out:
    out = out.replace('</actions>', gf_actions + '</actions>')

if out != s:
    import time
    open('%s.bak.%d' % (uca, time.time()), 'w').write(s)
    open(uca, 'w').write(out)
    print('OK: zmigrowano akcję terminala w %s (fallback chain)' % uca)
PYEOF
fi
echo "OK: branding zainstalowany"
