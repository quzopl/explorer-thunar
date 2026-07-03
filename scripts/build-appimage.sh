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

# 1. build z prefiksem /usr do AppDir
# --disable-introspection: bez tego build pada na 'Thunarx-3.0.typelib'
cd thunar-src
./configure --prefix=/usr --disable-static --disable-introspection
# pełne przebudowanie: po zmianie prefiksu stare obiekty mają zapieczone
# poprzednie ścieżki (DATADIR itd.)
make clean >/dev/null 2>&1 || true
make -j"$(nproc)"
make install DESTDIR="$AD"
cd "$ROOT"

# 2. branding + symlink + desktop
mkdir -p "$AD/usr/share/explorer/themes" "$AD/usr/share/applications"
install -m644 branding/themes/*.css "$AD/usr/share/explorer/themes/"
ln -sf thunar "$AD/usr/bin/explorer"
sed 's/^Exec=.*/Exec=explorer %F/; s/^Icon=.*/Icon=explorer/' \
    branding/explorer.desktop > "$AD/usr/share/applications/explorer.desktop"

# 3. ikona — własna z brandingu (bez zależności od zainstalowanego breeze)
mkdir -p "$AD/usr/share/icons/hicolor/scalable/apps"
install -m644 branding/explorer.svg "$AD/usr/share/icons/hicolor/scalable/apps/explorer.svg"

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

# 4. linuxdeploy + plugin gtk (NO_STRIP: stary strip nie zna .relr.dyn z Arch)
# libthunarx buduje się razem z Thunarem i leży tylko w AppDir — wskaż ją
# linuxdeployowi (bez systemowego Thunara nie ma jej skąd wziąć)
export LD_LIBRARY_PATH="$AD/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export DEPLOY_GTK_VERSION=3 NO_STRIP=1 OUTPUT=Explorer-x86_64.AppImage
# faza 1: zależności + hook środowiska GTK (bez pakowania)
linuxdeploy --appdir "$AD" \
  --executable "$AD/usr/bin/thunar" \
  --desktop-file "$AD/usr/share/applications/explorer.desktop" \
  --icon-file branding/explorer.svg \
  --plugin gtk

# dołóż GIO_MODULE_DIR do hooka (AppRun source'uje tylko hook pluginu gtk)
HOOK="$AD/apprun-hooks/linuxdeploy-plugin-gtk.sh"
if ! grep -q GIO_MODULE_DIR "$HOOK"; then
  printf '\nexport GIO_MODULE_DIR="$APPDIR/usr/lib/gio/modules" # gvfs hosta przez D-Bus\n' >> "$HOOK"
fi

# RUNPATH modułów wskazuje ścieżki dystrybucji builda (np.
# /usr/lib/x86_64-linux-gnu/gvfs), których nie ma na innych distro — wtedy
# dlopen modułu pada po cichu (libgvfscommon nieznajdowalna) i gvfs znika.
# Przestaw na bundlowane usr/lib.
patchelf --set-rpath '$ORIGIN/../..' "$AD"/usr/lib/gio/modules/*.so

# faza 2: spakuj AppImage
linuxdeploy --appdir "$AD" --output appimage
mkdir -p dist && mv -f Explorer-x86_64.AppImage dist/
echo "OK: dist/Explorer-x86_64.AppImage"
