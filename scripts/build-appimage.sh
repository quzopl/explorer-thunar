#!/usr/bin/env bash
# Buduje Explorer-x86_64.AppImage. Wymaga: linuxdeploy, linuxdeploy-plugin-gtk.sh,
# appimagetool w PATH (np. /tmp). Uruchom po fetch-sources + apply-patches.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"; AD="$ROOT/AppDir"

# allow tools downloaded to /tmp to be found by bare name
for t in linuxdeploy appimagetool; do
  command -v "$t" >/dev/null 2>&1 && continue
  for c in "/tmp/$t.AppImage" "/tmp/$t-x86_64.AppImage"; do
    [ -x "$c" ] && { ln -sf "$c" "/tmp/$t"; break; }
  done
done
export PATH="/tmp:$PATH"

# 0. zbuduj narzędzia ghostfs (userspace), jeśli jeszcze nie zbudowane
[ -x dist-ghostfs/ghostfs-cli ] || bash scripts/build-ghostfs.sh

# 1. build z prefiksem /usr do AppDir
# --disable-introspection: bez tego build pada na 'Thunarx-3.0.typelib'
cd thunar-src
./configure --prefix=/usr --disable-static --disable-introspection \
  --with-custom-thunarx-dirs-enabled
# pełne przebudowanie: po zmianie prefiksu stare obiekty mają zapieczone
# poprzednie ścieżki (DATADIR itd.)
make clean >/dev/null 2>&1 || true
EXPLORER_VERSION="${EXPLORER_VERSION_OVERRIDE:-$(git -C .. describe --tags --abbrev=0 2>/dev/null || echo dev)}"
make -j"$(nproc)" CPPFLAGS="-DEXPLORER_VERSION='\"$EXPLORER_VERSION\"'"
make install DESTDIR="$AD"
cd "$ROOT"

# 1a. oficjalne wtyczki (archive, media-tags) — do AppDir; ładowane przez
# THUNARX_DIRS z hooka (zaszyty katalog wtyczek to absolutna ścieżka hosta)
CONFIGURE_PREFIX=/usr DESTDIR="$AD" bash scripts/build-plugins.sh

# 2. branding + symlink + desktop
mkdir -p "$AD/usr/share/explorer/themes" "$AD/usr/share/applications"
install -m644 branding/themes/*.css "$AD/usr/share/explorer/themes/"
ln -sf thunar "$AD/usr/bin/explorer"
sed 's/^Exec=.*/Exec=explorer %F/; s/^Icon=.*/Icon=explorer/' \
    branding/explorer.desktop > "$AD/usr/share/applications/explorer.desktop"

# 3. ikona — własna z brandingu (bez zależności od zainstalowanego breeze)
mkdir -p "$AD/usr/share/icons/hicolor/scalable/apps"
install -m644 branding/explorer.svg "$AD/usr/share/icons/hicolor/scalable/apps/explorer.svg"

# 3c. narzędzia ghostfs (userspace) + owijki — z dist-ghostfs/ (zbudowane
# w kroku 0) i branding/ghostfs/; PATH do nich dowiązany w AppRun niżej
mkdir -p "$AD/usr/bin"
for b in ghostfs-cli ghostfs ghostfs-snapshot-gui ghostfs-disk-tool; do
  install -m755 "dist-ghostfs/$b" "$AD/usr/bin/$b"
done
install -m755 branding/ghostfs/gf-*.sh "$AD/usr/bin/"
install -m644 branding/ghostfs/gf-common.sh "$AD/usr/bin/"
install -m755 branding/explorer-action.sh "$AD/usr/bin/"

# 3d. domyślne szablony menu "Create Document" (zasiewane do katalogu XDG
# użytkownika przez hook przy starcie — patrz explorer-templates-seed.sh niżej)
mkdir -p "$AD/usr/share/explorer/templates"
cp -a branding/templates/. "$AD/usr/share/explorer/templates/"

# 3a. mostek GIO->gvfs: bundlowany libgio szuka modułów w ścieżce swojej
# dystrybucji (np. /usr/lib/x86_64-linux-gnu/gio/modules), której nie ma na
# innych distro — wtedy znikają Kosz/Recent/Computer/Network i dyski udisks2.
# Bundlujemy moduły i wskazujemy je przez GIO_MODULE_DIR (hook niżej);
# z demonami gvfs hosta rozmawiają one stabilnym protokołem D-Bus.
GIO_MOD_SRC="$(pkg-config --variable=giomoduledir gio-2.0 2>/dev/null || echo /usr/lib/x86_64-linux-gnu/gio/modules)"
mkdir -p "$AD/usr/lib/gio/modules"
for m in libgvfsdbus.so libgioremote-volume-monitor.so; do
  [ -f "$GIO_MOD_SRC/$m" ] && install -m755 "$GIO_MOD_SRC/$m" "$AD/usr/lib/gio/modules/"
done

# 3b. pomocnik uruchamiania aplikacji: bundlowany libgio odpala programy przez
# gio-launch-desktop spod zaszytej ścieżki dystrybucji builda — na innych
# distro jej nie ma i KAŻDE otwarcie pliku/aplikacji pada ("No such file or
# directory"). Bundlujemy binarkę i wskazujemy ją przez GIO_LAUNCH_DESKTOP.
GLD="$(pkg-config --variable=libdir glib-2.0 2>/dev/null || echo /usr/lib/x86_64-linux-gnu)/glib-2.0/gio-launch-desktop"
[ -f "$GLD" ] || GLD=/usr/libexec/gio-launch-desktop
mkdir -p "$AD/usr/libexec"
install -m755 "$GLD" "$AD/usr/libexec/gio-launch-desktop"

# 4. linuxdeploy + plugin gtk (NO_STRIP: stary strip nie zna .relr.dyn z Arch)
# libthunarx buduje się razem z Thunarem i leży tylko w AppDir — wskaż ją
# linuxdeployowi (bez systemowego Thunara nie ma jej skąd wziąć)
export LD_LIBRARY_PATH="$AD/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export DEPLOY_GTK_VERSION=3 NO_STRIP=1 OUTPUT=Explorer-x86_64.AppImage
# faza 1: zależności + hook środowiska GTK (bez pakowania)
# --executable dla binarek ghostfs: to jest tu jedyny mechanizm domykania
# zależności (ldd-closure) — linuxdeploy sam dociąga i bundluje wszystkie
# nieoczywiste biblioteki współdzielone (libfuse3, libcrypto, libgtk-3...)
# każdej podanej binarki do $AD/usr/lib, tak jak już robi to dla thunara.
GF_EXE_ARGS=()
for so in "$AD"/usr/bin/ghostfs "$AD"/usr/bin/ghostfs-cli \
          "$AD"/usr/bin/ghostfs-snapshot-gui "$AD"/usr/bin/ghostfs-disk-tool; do
  [ -x "$so" ] && GF_EXE_ARGS+=(--executable "$so")
done
linuxdeploy --appdir "$AD" \
  --executable "$AD/usr/bin/thunar" \
  "${GF_EXE_ARGS[@]}" \
  --desktop-file "$AD/usr/share/applications/explorer.desktop" \
  --icon-file branding/explorer.svg \
  --plugin gtk

# dołóż GIO_MODULE_DIR do hooka (AppRun source'uje tylko hook pluginu gtk)
HOOK="$AD/apprun-hooks/linuxdeploy-plugin-gtk.sh"
if ! grep -q GIO_MODULE_DIR "$HOOK"; then
  printf '\nexport GIO_MODULE_DIR="$APPDIR/usr/lib/gio/modules" # gvfs hosta przez D-Bus\n' >> "$HOOK"
fi
if ! grep -q GIO_LAUNCH_DESKTOP "$HOOK"; then
  printf 'export GIO_LAUNCH_DESKTOP="$APPDIR/usr/libexec/gio-launch-desktop" # uruchamianie aplikacji\n' >> "$HOOK"
fi
if ! grep -q THUNARX_DIRS "$HOOK"; then
  printf 'export THUNARX_DIRS="$APPDIR/usr/lib/thunarx-3" # bundlowane wtyczki\n' >> "$HOOK"
fi

# akcje UCA dla użytkowników AppImage: zasiej ~/.config/Thunar/uca.xml z
# szablonu, a istniejącemu dołóż akcję "Open in Terminal", jeśli jej brak
# (użytkownicy AppImage nie uruchamiają install-branding.sh)
cat > "$AD/usr/bin/explorer-uca-setup.sh" <<'EOSETUP'
#!/bin/sh
# idempotentna migracja akcji UCA (wołana z AppRun przy każdym starcie)
TPL="$APPDIR/usr/etc/xdg/Thunar/uca.xml"
[ -f "$TPL" ] || TPL="$APPDIR/etc/xdg/Thunar/uca.xml"
UCA="${XDG_CONFIG_HOME:-$HOME/.config}/Thunar/uca.xml"
[ -f "$TPL" ] || exit 0
# an empty or cut-off uca.xml leaves the context menu with no actions at all,
# and nothing else repairs it: keep it aside and seed afresh
if [ -f "$UCA" ] && ! grep -q '</actions>' "$UCA"; then
  mv "$UCA" "$UCA.broken.$(date +%s)"
  notify-send -a Explorer -i dialog-warning "Explorer repaired its right-click actions" \
    "uca.xml was empty or damaged; the old file was kept as $(basename "$UCA").broken.*" 2>/dev/null
fi
if [ ! -f "$UCA" ]; then
  mkdir -p "$(dirname "$UCA")" && cp "$TPL" "$UCA"
  exit 0
fi
grep -q 'Open in Terminal' "$UCA" && exit 0
BLK="$(mktemp)" || exit 0
awk '/<action>/{buf="";inA=1} inA{buf=buf $0 "\n"} /<\/action>/{inA=0; if (buf ~ /Open in Terminal/) blk=buf} END{printf "%s", blk}' "$TPL" > "$BLK"
[ -s "$BLK" ] || { rm -f "$BLK"; exit 0; }
cp "$UCA" "$UCA.bak.appimage" 2>/dev/null
TMP="$(mktemp)" || { rm -f "$BLK"; exit 0; }
awk -v f="$BLK" '/<\/actions>/{while ((getline l < f) > 0) print l} {print}' "$UCA" > "$TMP" && mv "$TMP" "$UCA"
rm -f "$BLK"
EOSETUP
chmod 755 "$AD/usr/bin/explorer-uca-setup.sh"
if ! grep -q explorer-uca-setup "$HOOK"; then
  printf 'sh "$APPDIR/usr/bin/explorer-uca-setup.sh" 2>/dev/null || true # akcje UCA\n' >> "$HOOK"
fi

# akcje ghostfs w uca.xml dla użytkowników AppImage: szablon (uca.xml.in,
# patch 44) ma je już wbudowane, więc świeżo zasiany plik jest kompletny;
# ten hook dokłada je idempotentnie istniejącym userom, których uca.xml
# powstał zanim akcje ghostfs istniały (ta sama logika co Task 4 / Python
# w scripts/install-branding.sh, tu jako samodzielny skrypt na start AppRun)
cat > "$AD/usr/bin/explorer-ghostfs-seed.sh" <<'EOGFSEED'
#!/bin/sh
# idempotentne zasianie/domigrowanie akcji ghostfs w uca.xml (wołane z AppRun)
UCA="${XDG_CONFIG_HOME:-$HOME/.config}/Thunar/uca.xml"
if [ ! -f "$UCA" ]; then
  TPL="$APPDIR/usr/etc/xdg/Thunar/uca.xml"
  [ -f "$TPL" ] || TPL="$APPDIR/etc/xdg/Thunar/uca.xml"
  [ -f "$TPL" ] || exit 0
  mkdir -p "$(dirname "$UCA")" && cp "$TPL" "$UCA"
  exit 0
fi
command -v python3 >/dev/null 2>&1 || exit 0
UCA_FILE="$UCA" python3 - <<'PYEOF'
import os
uca = os.environ['UCA_FILE']
s = open(uca).read()
out = s

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
ex_actions = '''  <action>
    <icon>edit-copy-path</icon>
    <patterns>*</patterns>
    <name>Copy Path</name>
    <command>explorer-action.sh copy-path %F</command>
    <description>Copy the full path of the selection to the clipboard</description>
    <directories/>
    <audio-files/>
    <image-files/>
    <other-files/>
    <text-files/>
    <video-files/>
  </action>
  <action>
    <icon>security-high</icon>
    <patterns>*</patterns>
    <name>SHA-256 Checksum</name>
    <command>explorer-action.sh checksum %F</command>
    <description>Show the SHA-256 checksum and copy it to the clipboard</description>
    <audio-files/>
    <image-files/>
    <other-files/>
    <text-files/>
    <video-files/>
  </action>
  <action>
    <icon>document-compare</icon>
    <patterns>*</patterns>
    <range>2-2</range>
    <name>Compare Files</name>
    <command>explorer-action.sh compare %F</command>
    <description>Compare the two selected files</description>
    <other-files/>
    <text-files/>
  </action>
  <action>
    <icon>kdeconnect</icon>
    <patterns>*</patterns>
    <name>Send to Phone</name>
    <command>explorer-action.sh send-phone %F</command>
    <description>Send the selection to a phone with KDE Connect</description>
    <audio-files/>
    <image-files/>
    <other-files/>
    <text-files/>
    <video-files/>
  </action>
'''

def sync_actions(out, command_re, actions):
    # actions are matched by their command; the set is replaced only when its
    # names differ, since Thunar re-saves uca.xml in its own layout (tabs,
    # unique-id) and a text comparison would rewrite the file on every start
    one = r'[ \t]*<action>(?:(?!</action>).)*?<command>' + command_re + r'(?:(?!</action>).)*?</action>\n?'
    names = lambda xml: sorted(re.findall(r'<name>([^<]*)</name>', xml))
    if names(''.join(re.findall(one, out, flags=re.S))) == names(actions):
        return out
    out = re.sub(one, '', out, flags=re.S)
    return out.replace('</actions>', actions + '</actions>') if '</actions>' in out else out

out = sync_actions(out, r'gf-[^<]*</command>', gf_actions)
out = sync_actions(out, r'explorer-action\.sh [^<]*</command>', ex_actions)

if out != s and '</actions>' in out:
    import time
    open('%s.bak.%d' % (uca, time.time()), 'w').write(s)
    # writing in place truncates first: an interrupted write (full disk, killed
    # process) left uca.xml empty and the context menu without any actions
    with open(uca + '.tmp', 'w') as f:
        f.write(out)
        f.flush()
        os.fsync(f.fileno())
    os.replace(uca + '.tmp', uca)
    # one backup per change: keep the five newest
    import glob
    for old in sorted(glob.glob(uca + '.bak.[0-9]*'), key=os.path.getmtime)[:-5]:
        os.remove(old)
PYEOF
EOGFSEED
chmod 755 "$AD/usr/bin/explorer-ghostfs-seed.sh"
if ! grep -q explorer-ghostfs-seed "$HOOK"; then
  printf 'sh "$APPDIR/usr/bin/explorer-ghostfs-seed.sh" 2>/dev/null || true # akcje ghostfs w uca.xml\n' >> "$HOOK"
fi

# domyślne szablony "Create Document" dla użytkowników AppImage: bez nich menu
# jest puste ("brak szablonów w katalogu domowym"). Katalog szablonów jest
# LOKALIZOWANY (~/Templates, ~/Szablony, ~/Vorlagen...), więc czytamy go z
# user-dirs.dirs zamiast zaszywać ~/Templates. Zasiewamy tylko pusty katalog.
cat > "$AD/usr/bin/explorer-templates-seed.sh" <<'EOTPL'
#!/bin/sh
# idempotentne zasianie domyślnych szablonów (wołane z AppRun przy starcie)
SRC="$APPDIR/usr/share/explorer/templates"
[ -d "$SRC" ] || exit 0

T=""
if command -v xdg-user-dir >/dev/null 2>&1; then
  T="$(xdg-user-dir TEMPLATES 2>/dev/null)"
fi
if [ -z "$T" ] || [ "$T" = "$HOME" ]; then
  UD="${XDG_CONFIG_HOME:-$HOME/.config}/user-dirs.dirs"
  if [ -f "$UD" ]; then
    # bez source'owania pliku (to by wykonało jego zawartość) — sam odczyt
    T="$(sed -n 's/^[[:space:]]*XDG_TEMPLATES_DIR="\(.*\)"[[:space:]]*$/\1/p' "$UD" | tail -1)"
    T="$(printf '%s' "$T" | sed "s|^\$HOME|$HOME|")"
  fi
fi
if [ -z "$T" ] || [ "$T" = "$HOME" ]; then
  T="$HOME/Templates"
fi

mkdir -p "$T" 2>/dev/null || exit 0
# katalog niepusty = użytkownik ma własne szablony; nie dotykamy
[ -z "$(ls -A "$T" 2>/dev/null)" ] || exit 0

for f in "$SRC"/*; do
  [ -f "$f" ] || continue
  b="${f##*/}"
  cp "$f" "$T/$b" 2>/dev/null || continue
  case "$b" in
    *.sh) chmod 755 "$T/$b" 2>/dev/null ;;
    *)    chmod 644 "$T/$b" 2>/dev/null ;;
  esac
done
EOTPL
chmod 755 "$AD/usr/bin/explorer-templates-seed.sh"
if ! grep -q explorer-templates-seed "$HOOK"; then
  printf 'sh "$APPDIR/usr/bin/explorer-templates-seed.sh" 2>/dev/null || true # domyślne szablony\n' >> "$HOOK"
fi

# RUNPATH modułów wskazuje ścieżki dystrybucji builda (np.
# /usr/lib/x86_64-linux-gnu/gvfs), których nie ma na innych distro — wtedy
# dlopen modułu pada po cichu (libgvfscommon nieznajdowalna) i gvfs znika.
# Przestaw na bundlowane usr/lib.
patchelf --set-rpath '$ORIGIN/../..' "$AD"/usr/lib/gio/modules/*.so
patchelf --set-rpath '$ORIGIN/..' "$AD"/usr/lib/thunarx-3/*.so

# 4a. PATH do narzędzi ghostfs (i innych binarek w usr/bin) w AppRun.
# linuxdeploy REGENERUJE AppRun przy każdym wywołaniu (także --output appimage),
# więc eksport PATH musi trafić do AppRun TUŻ przed pakowaniem, a pakujemy
# bezpośrednio appimagetoolem (linuxdeploy --output i tak tylko go opakowuje,
# ale przy okazji nadpisałby AppRun i skasował ten wiersz). $APPDIR ustawia
# w środowisku runtime AppImage; hook GTK jest nadal source'owany wyżej w AppRun.
if ! grep -q 'PATH="$APPDIR/usr/bin' "$AD/AppRun"; then
  sed -i '/^exec /i export PATH="$APPDIR/usr/bin:${PATH:-/usr/bin:/bin}" # narzędzia ghostfs (gf-*.sh, ghostfs-cli, ...)' "$AD/AppRun"
fi

# faza 2: spakuj AppImage z informacją aktualizacyjną zsync (AppImageUpdate
# pobiera wtedy tylko różnice między wydaniami z GitHub Releases). Używamy
# appimagetoola wprost (nie linuxdeploy --output), żeby nie regenerował AppRun.
export ARCH=x86_64
appimagetool -n \
  -u "gh-releases-zsync|quzopl|explorer-thunar|latest|Explorer-x86_64.AppImage.zsync" \
  "$AD" Explorer-x86_64.AppImage
mkdir -p dist && mv -f Explorer-x86_64.AppImage dist/
mv -f Explorer-x86_64.AppImage.zsync dist/ 2>/dev/null || true
echo "OK: dist/Explorer-x86_64.AppImage"
