#!/usr/bin/env bash
# Generuje zrzuty ekranu do docs/screenshots/ na FEJKOWYCH danych (bez danych
# osobistych) — tworzy tymczasowy „dom" z przykładowymi katalogami/plikami,
# przełącza kolejno motywy i łapie SAMO okno aplikacji (KDE: spectacle -a).
#
# Uruchom w swojej sesji graficznej (NIE przez sandbox):
#   bash scripts/gen-screenshots.sh
#
# Wymaga: zbudowanego install/bin/explorer, spectacle (KDE), convert (ImageMagick).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
BIN="$ROOT/install/bin/explorer"
OUT="$ROOT/docs/screenshots"
DEMO="${TMPDIR:-/tmp}/explorer-demo"

[ -x "$BIN" ] || { echo "Brak $BIN — najpierw zbuduj (scripts/build.sh)." >&2; exit 1; }
command -v spectacle >/dev/null || { echo "Brak 'spectacle'." >&2; exit 1; }
command -v convert  >/dev/null || { echo "Brak 'convert' (imagemagick)." >&2; exit 1; }

# --- fejkowy dom z przykładową zawartością ---------------------------------
make_demo() {
  rm -rf "$DEMO"
  mkdir -p "$DEMO"/{Desktop,Documents,Downloads,Music,Pictures,Videos,Projects,Work}
  : > "$DEMO/Documents/Report.docx"; : > "$DEMO/Documents/Invoice.pdf"
  : > "$DEMO/Documents/Notes.txt";   : > "$DEMO/Documents/Budget.xlsx"
  : > "$DEMO/Documents/Letter.odt"
  : > "$DEMO/Downloads/setup.zip";   : > "$DEMO/Downloads/archive.tar.gz"
  : > "$DEMO/Downloads/song.mp3";    : > "$DEMO/Downloads/clip.mp4"
  mkdir -p "$DEMO/Projects/website" "$DEMO/Projects/mobile-app"
  : > "$DEMO/Projects/script.py"; : > "$DEMO/Projects/index.html"
  : > "$DEMO/Projects/style.css"; : > "$DEMO/Projects/README.md"
  : > "$DEMO/welcome.txt"; : > "$DEMO/todo.md"
  convert -size 640x480 gradient:'#4d8bff'-'#88c0d0' "$DEMO/Pictures/sunrise.jpg"
  convert -size 640x480 gradient:'#2e3440'-'#5e81ac' "$DEMO/Pictures/mountains.jpg"
  convert -size 600x600 plasma:fractal              "$DEMO/Pictures/abstract.png"
  convert -size 800x500 gradient:'#f6f6f6'-'#3b82f6' "$DEMO/Pictures/sky.jpg"
}

# slug_motywu -> nazwa_pliku_wyjściowego
SHOTS=(
  "fluent-dark:01-fluent-dark.png"
  "cobalt-dark:02-cobalt-dark.png"
  "aurora-light:03-aurora-light.png"
  "porcelain-light:04-porcelain-light.png"
)

mkdir -p "$OUT"
make_demo
BAK="$(xfconf-query -c explorer -p /explorer-theme 2>/dev/null || echo fluent-dark)"
echo "Zapisany bieżący motyw: $BAK"

for entry in "${SHOTS[@]}"; do
  slug="${entry%%:*}"; png="${entry##*:}"
  echo ">> $slug -> docs/screenshots/$png"
  pkill -f "$BIN" 2>/dev/null || true
  sleep 1
  xfconf-query -c explorer -p /explorer-theme -s "$slug"
  HOME="$DEMO" "$BIN" "$DEMO" >/dev/null 2>&1 &
  sleep 4                       # daj oknu się otworzyć i wyrenderować
  spectacle -a -b -n -o "$OUT/$png"   # -a: aktywne okno, -b: bez GUI, -n: bez powiadomień
  sleep 1
done

pkill -f "$BIN" 2>/dev/null || true
xfconf-query -c explorer -p /explorer-theme -s "$BAK"
echo "Przywrócono motyw: $BAK"
echo "Gotowe. Zrzuty w: $OUT"
ls -la "$OUT"
