#!/usr/bin/env bash
# Buduje oficjalne wtyczki Thunara i instaluje je do prefiksu Explorera:
#  - thunar-archive-plugin    (Extract Here / Extract To / Create Archive
#                              w menu — deleguje do ark/file-roller/xarchiver)
#  - thunar-media-tags-plugin (zakładka tagów audio we Właściwościach,
#                              tryb "Audio tags" w masowej zmianie nazw; taglib)
#
# Użycie:
#   bash scripts/build-plugins.sh                 # do ./install (po build.sh)
#   CONFIGURE_PREFIX=/usr DESTDIR=$AD \
#     bash scripts/build-plugins.sh               # wariant dla AppImage
#
# Wymaga: zbudowanego Explorera (thunarx-3.pc w PREFIX/lib/pkgconfig),
# libtag (taglib) z nagłówkami dla media-tags.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
PREFIX="$ROOT/install"
CONFIGURE_PREFIX="${CONFIGURE_PREFIX:-$PREFIX}"
DESTDIR="${DESTDIR:-}"

VER_ARCHIVE=0.6.0
VER_MEDIA=0.6.0

export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"

pkg-config --exists thunarx-3 || {
  echo "Brak thunarx-3.pc w $PREFIX/lib/pkgconfig — najpierw scripts/build.sh" >&2
  exit 1
}

mkdir -p .cache plugins-src

fetch() { # $1 = nazwa, $2 = wersja
  local series="${2%.*}"
  local tb="$1-$2.tar.xz"
  [ -f ".cache/$tb" ] || curl -fL --retry 3 -o ".cache/$tb" \
    "https://archive.xfce.org/src/thunar-plugins/$1/$series/$tb"
  rm -rf "plugins-src/$1-$2"
  tar xJf ".cache/$tb" -C plugins-src
}

fetch thunar-archive-plugin "$VER_ARCHIVE"
fetch thunar-media-tags-plugin "$VER_MEDIA"

# archive-plugin szuka skryptów .tap pod zaszytym LIBEXECDIR (absolutnym) —
# w AppImage to ścieżka hosta. Uczul lookup na $APPDIR.
TAPC="plugins-src/thunar-archive-plugin-$VER_ARCHIVE/thunar-archive-plugin/tap-backend.c"
TAPC="$TAPC" python3 - <<'PYEOF'
import os
p = os.environ['TAPC']
s = open(p).read()
old = ('filename = g_strdup_printf (LIBEXECDIR G_DIR_SEPARATOR_S '
       '"thunar-archive-plugin" G_DIR_SEPARATOR_S "%s.tap", base_name);')
new = ('{ const gchar *tap_appdir = g_getenv ("APPDIR"); '
       'if (tap_appdir != NULL && *tap_appdir != \'\\0\') '
       'filename = g_strdup_printf ("%s/usr/libexec/thunar-archive-plugin/%s.tap", tap_appdir, base_name); '
       'else '
       'filename = g_strdup_printf (LIBEXECDIR G_DIR_SEPARATOR_S '
       '"thunar-archive-plugin" G_DIR_SEPARATOR_S "%s.tap", base_name); }')
if old in s:
    open(p, 'w').write(s.replace(old, new, 1))
    print('tap-backend.c: lookup .tap świadomy $APPDIR')
elif 'tap_appdir' in s:
    print('tap-backend.c: już spatchowany')
else:
    raise SystemExit('tap-backend.c: nie znaleziono wzorca do podmiany')
PYEOF

for d in "plugins-src/thunar-archive-plugin-$VER_ARCHIVE" \
         "plugins-src/thunar-media-tags-plugin-$VER_MEDIA"; do
  (
    cd "$d"
    # tarballe 0.6.x nie zawierają wygenerowanego configure — potrzebne
    # xfce4-dev-tools (xdt-autogen) + autotools
    if [ ! -x configure ]; then
      NOCONFIGURE=1 ./autogen.sh >autogen.log 2>&1 \
        || { tail -5 autogen.log >&2; exit 1; }
    fi
    ./configure --prefix="$CONFIGURE_PREFIX" --disable-static >configure.log 2>&1 \
      || { tail -5 configure.log >&2; exit 1; }
    make -j"$(nproc)" >build.log 2>&1 || { tail -5 build.log >&2; exit 1; }
    make install ${DESTDIR:+DESTDIR="$DESTDIR"} >install.log 2>&1 \
      || { tail -5 install.log >&2; exit 1; }
  )
  echo "OK: $(basename "$d")"
done

echo "OK: wtyczki zainstalowane (${DESTDIR:-$CONFIGURE_PREFIX})"
