#!/usr/bin/env bash
# Instaluje Explorer 2.0 (NOVA shell, GTK4) dla bieżącego użytkownika:
#  - launcher `explorer-nova` w ~/.local/bin
#  - wpis .desktop (menu/pasek zadań) + ikona + font Space Grotesk
# Wymaga: python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1 (na Debian/Ubuntu);
#         python-gobject, gtk4, libadwaita (na Arch).
set -euo pipefail
cd "$(dirname "$0")"
SRC="$PWD"
BIN="${XDG_DATA_HOME:-$HOME/.local}/../bin"; BIN="$HOME/.local/bin"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
FONTS="${XDG_DATA_HOME:-$HOME/.local/share}/fonts"

# sprawdź zależności
python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1'); \
from gi.repository import Gtk, Adw" 2>/dev/null || {
  echo "BŁĄD: brak GTK4/libadwaita/PyGObject." >&2
  echo "  Ubuntu/Debian: sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1" >&2
  echo "  Arch:          sudo pacman -S python-gobject gtk4 libadwaita" >&2
  exit 1
}

mkdir -p "$BIN" "$APPS" "$ICONS" "$FONTS"

# launcher
cat > "$BIN/explorer-nova" <<EOF
#!/usr/bin/env bash
exec python3 "$SRC/app.py" "\$@"
EOF
chmod +x "$BIN/explorer-nova"

# .desktop (Exec z pełną ścieżką launchera)
sed "s|^Exec=.*|Exec=$BIN/explorer-nova %f|" explorer-nova.desktop > "$APPS/explorer-nova.desktop"

# ikona + font (współdzielone z 1.x)
[ -f ../branding/explorer.svg ] && install -m644 ../branding/explorer.svg "$ICONS/explorer.svg" || true
[ -f ../branding/fonts/SpaceGrotesk.ttf ] && install -m644 ../branding/fonts/SpaceGrotesk.ttf "$FONTS/" || true
fc-cache -f "$FONTS" 2>/dev/null || true
update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" 2>/dev/null || true

echo "OK: zainstalowano Explorer 2.0."
echo "Uruchom z menu (Explorer) lub: explorer-nova"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "Uwaga: $BIN nie jest w PATH — dodaj je lub uruchamiaj pełną ścieżką.";; esac
