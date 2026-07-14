#!/usr/bin/env bash
# Buduje Explorer-NOVA-x86_64.AppImage — samodzielna paczka apki GTK4/Python.
# Bundluje: Python 3 + stdlib, PyGObject (gi) + cairo, typelibs GI, libgtk-4,
# libadwaita, loadery gdk-pixbuf, schematy GLib, font. Uruchom na Ubuntu 24.04
# (GTK 4.14). Wymaga appimagetool w PATH lub /tmp.
set -euo pipefail
cd "$(dirname "$0")"
SRC="$PWD"; ROOT="$SRC/.."; AD="$SRC/AppDir"
ARCH_TRIPLET="x86_64-linux-gnu"
PYVER="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
LIBDIR="/usr/lib/$ARCH_TRIPLET"
GIR="$LIBDIR/girepository-1.0"

command -v appimagetool >/dev/null 2>&1 || { [ -x /tmp/appimagetool ] && export PATH="/tmp:$PATH"; }
command -v appimagetool >/dev/null 2>&1 || { echo "Brak appimagetool w PATH/tmp" >&2; exit 1; }

rm -rf "$AD"; mkdir -p "$AD/usr/bin" "$AD/usr/lib" "$AD/usr/share"

echo ">> Python interpreter + stdlib"
cp "$(readlink -f "$(command -v python3)")" "$AD/usr/bin/python3"
mkdir -p "$AD/usr/lib/python$PYVER"
# stdlib bez ciężkich testów
( cd "/usr/lib/python$PYVER" && \
  tar cf - --exclude='test' --exclude='tests' --exclude='__pycache__' \
      --exclude='idlelib' --exclude='turtledemo' . ) | ( cd "$AD/usr/lib/python$PYVER" && tar xf - )
# lib-dynload (moduły C stdlib)
[ -d "/usr/lib/python$PYVER/lib-dynload" ] && cp -r "/usr/lib/python$PYVER/lib-dynload" "$AD/usr/lib/python$PYVER/" || true

echo ">> PyGObject (gi) + cairo"
mkdir -p "$AD/usr/lib/python3/dist-packages"
cp -r /usr/lib/python3/dist-packages/gi "$AD/usr/lib/python3/dist-packages/"
for m in cairo pycairo; do
  [ -d "/usr/lib/python3/dist-packages/$m" ] && cp -r "/usr/lib/python3/dist-packages/$m" "$AD/usr/lib/python3/dist-packages/" || true
done
cp /usr/lib/python3/dist-packages/*cairo*.so "$AD/usr/lib/python3/dist-packages/" 2>/dev/null || true

echo ">> typelibs GI"
mkdir -p "$AD/usr/lib/girepository-1.0"
for t in Gtk-4.0 Gdk-4.0 Gsk-4.0 Adw-1 Gio-2.0 GioUnix-2.0 GLib-2.0 GLibUnix-2.0 \
         GObject-2.0 GdkPixbuf-2.0 Pango-1.0 PangoCairo-1.0 Graphene-1.0 \
         HarfBuzz-0.0 cairo-1.0 freetype2-2.0 Gio-2.0; do
  [ -f "$GIR/$t.typelib" ] && cp "$GIR/$t.typelib" "$AD/usr/lib/girepository-1.0/" || true
done

echo ">> loadery gdk-pixbuf"
PB_SRC="$(dirname "$(ls "$LIBDIR"/gdk-pixbuf-2.0/*/loaders.cache 2>/dev/null | head -1)")"
mkdir -p "$AD/usr/lib/gdk-pixbuf-2.0/loaders"
cp "$PB_SRC"/loaders/*.so "$AD/usr/lib/gdk-pixbuf-2.0/loaders/" 2>/dev/null || true

echo ">> zbieranie zależności .so (domknięcie ldd)"
gather() {  # $1 = plik ELF; dopisuje jego biblioteki do AppDir/usr/lib
  ldd "$1" 2>/dev/null | awk '/=> \//{print $3}' | while read -r so; do
    case "$so" in
      /lib/ld-*|*/ld-linux*) continue;;   # loader zostawiamy hostowi
    esac
    bn="$(basename "$so")"
    [ -f "$AD/usr/lib/$bn" ] || cp -L "$so" "$AD/usr/lib/$bn"
  done
}
SEEDS=("$AD/usr/bin/python3" "$LIBDIR/libgtk-4.so.1" "$LIBDIR/libadwaita-1.so.0")
for so in "$AD"/usr/lib/python3/dist-packages/gi/*.so \
          "$AD"/usr/lib/gdk-pixbuf-2.0/loaders/*.so \
          "$AD"/usr/lib/python"$PYVER"/lib-dynload/*.so; do
  [ -f "$so" ] && SEEDS+=("$so")
done
for s in "${SEEDS[@]}"; do gather "$s"; done
# libgtk-4 i libadwaita same w sobie
cp -L "$LIBDIR/libgtk-4.so.1" "$AD/usr/lib/" 2>/dev/null || true
cp -L "$LIBDIR/libadwaita-1.so.0" "$AD/usr/lib/" 2>/dev/null || true
# druga tura: domknij zależności właśnie skopiowanych bibliotek
for so in "$AD"/usr/lib/*.so*; do gather "$so"; done
for so in "$AD"/usr/lib/*.so*; do gather "$so"; done

echo ">> schematy GLib"
mkdir -p "$AD/usr/share/glib-2.0/schemas"
cp /usr/share/glib-2.0/schemas/org.gtk.*.gschema.xml "$AD/usr/share/glib-2.0/schemas/" 2>/dev/null || true
cp /usr/share/glib-2.0/schemas/*Adwaita*.gschema.xml "$AD/usr/share/glib-2.0/schemas/" 2>/dev/null || true
cp /usr/share/glib-2.0/schemas/gschemas.compiled "$AD/usr/share/glib-2.0/schemas/" 2>/dev/null || \
  glib-compile-schemas "$AD/usr/share/glib-2.0/schemas" 2>/dev/null || true
glib-compile-schemas "$AD/usr/share/glib-2.0/schemas" 2>/dev/null || true

echo ">> ikony motywu (Adwaita/hicolor symbolic) — potrzebne dla ikon UI"
for it in Adwaita hicolor; do
  [ -d "/usr/share/icons/$it" ] && { mkdir -p "$AD/usr/share/icons/$it"; \
    cp -r "/usr/share/icons/$it/scalable" "$AD/usr/share/icons/$it/" 2>/dev/null || true; \
    cp -r "/usr/share/icons/$it/symbolic" "$AD/usr/share/icons/$it/" 2>/dev/null || true; \
    cp "/usr/share/icons/$it/index.theme" "$AD/usr/share/icons/$it/" 2>/dev/null || true; }
done
# pełna Adwaita bywa duża — weź symboliczne + index
mkdir -p "$AD/usr/share/icons/Adwaita"
cp -r /usr/share/icons/Adwaita/symbolic "$AD/usr/share/icons/Adwaita/" 2>/dev/null || true
cp -rn /usr/share/icons/Adwaita/scalable "$AD/usr/share/icons/Adwaita/" 2>/dev/null || true
cp /usr/share/icons/Adwaita/index.theme "$AD/usr/share/icons/Adwaita/" 2>/dev/null || true
gtk-update-icon-cache -q "$AD/usr/share/icons/Adwaita" 2>/dev/null || true

echo ">> aplikacja, font, ikona, .desktop"
mkdir -p "$AD/usr/share/explorer-nova" "$AD/usr/share/fonts"
cp "$SRC/app.py" "$SRC/style.css" "$AD/usr/share/explorer-nova/"
[ -f "$ROOT/branding/fonts/SpaceGrotesk.ttf" ] && cp "$ROOT/branding/fonts/SpaceGrotesk.ttf" "$AD/usr/share/fonts/" || true
[ -f "$ROOT/branding/explorer.svg" ] && cp "$ROOT/branding/explorer.svg" "$AD/explorer.svg" || true
cat > "$AD/explorer-nova.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Explorer
Comment=NOVA-style file manager (GTK4)
Exec=explorer-nova %f
Icon=explorer
Categories=System;Utility;FileManager;
Terminal=false
StartupWMClass=explorer
EOF

echo ">> AppRun"
cat > "$AD/AppRun" <<'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
PYVER="$(ls "$HERE/usr/lib" | grep -oE 'python3\.[0-9]+' | head -1)"
export LD_LIBRARY_PATH="$HERE/usr/lib:${LD_LIBRARY_PATH:-}"
export PYTHONHOME="$HERE/usr"
export PYTHONPATH="$HERE/usr/lib/$PYVER:$HERE/usr/lib/$PYVER/lib-dynload:$HERE/usr/lib/python3/dist-packages"
export PYTHONDONTWRITEBYTECODE=1
export GI_TYPELIB_PATH="$HERE/usr/lib/girepository-1.0"
export GDK_PIXBUF_MODULEDIR="$HERE/usr/lib/gdk-pixbuf-2.0/loaders"
export GDK_PIXBUF_MODULE_FILE="$HERE/usr/lib/gdk-pixbuf-2.0/loaders.cache"
export GSETTINGS_SCHEMA_DIR="$HERE/usr/share/glib-2.0/schemas"
export XDG_DATA_DIRS="$HERE/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
export FONTCONFIG_PATH="${FONTCONFIG_PATH:-/etc/fonts}"
# odbuduj cache loaderów pod właściwe ścieżki (raz)
if [ ! -f "$GDK_PIXBUF_MODULE_FILE" ] && command -v gdk-pixbuf-query-loaders >/dev/null; then
  GDK_PIXBUF_MODULEDIR="$GDK_PIXBUF_MODULEDIR" gdk-pixbuf-query-loaders > "$GDK_PIXBUF_MODULE_FILE" 2>/dev/null || true
fi
exec "$HERE/usr/bin/python3" "$HERE/usr/share/explorer-nova/app.py" "$@"
EOF
chmod +x "$AD/AppRun"

# cache loaderów gdk-pixbuf (ścieżki podmieni AppRun, ale wygeneruj bazowy)
if command -v gdk-pixbuf-query-loaders >/dev/null; then
  GDK_PIXBUF_MODULEDIR="$AD/usr/lib/gdk-pixbuf-2.0/loaders" \
    gdk-pixbuf-query-loaders > "$AD/usr/lib/gdk-pixbuf-2.0/loaders.cache" 2>/dev/null || true
fi

echo ">> pakowanie"
[ -f "$AD/explorer.svg" ] && ln -sf explorer.svg "$AD/.DirIcon" 2>/dev/null || true
mkdir -p "$ROOT/dist"
ARCH=x86_64 appimagetool --no-appstream "$AD" "$ROOT/dist/Explorer-NOVA-x86_64.AppImage"
echo "OK: dist/Explorer-NOVA-x86_64.AppImage"
