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

# 4. linuxdeploy + plugin gtk (NO_STRIP: stary strip nie zna .relr.dyn z Arch)
export DEPLOY_GTK_VERSION=3 NO_STRIP=1 OUTPUT=Explorer-x86_64.AppImage
linuxdeploy --appdir "$AD" \
  --executable "$AD/usr/bin/thunar" \
  --desktop-file "$AD/usr/share/applications/explorer.desktop" \
  --icon-file branding/explorer.svg \
  --plugin gtk --output appimage
mkdir -p dist && mv -f Explorer-x86_64.AppImage dist/
echo "OK: dist/Explorer-x86_64.AppImage"
