# wspólne helpery owijek ghostfs — sourced, nie uruchamiane
gf_have() { command -v "$1" >/dev/null 2>&1; }

gf_err() {
  if gf_have zenity; then zenity --error --no-wrap --text "$1" 2>/dev/null
  elif gf_have kdialog; then kdialog --error "$1" 2>/dev/null
  else printf 'ghostfs: %s\n' "$1" >&2; fi
}

gf_info() {
  if gf_have zenity; then zenity --info --no-wrap --text "$1" 2>/dev/null
  elif gf_have kdialog; then kdialog --msgbox "$1" 2>/dev/null
  else printf 'ghostfs: %s\n' "$1"; fi
}

gf_entry() { # $1=tytuł $2=domyślne -> stdout wpisany tekst (pusty = anulowano)
  if gf_have zenity; then zenity --entry --title "$1" --text "$1" --entry-text "$2" 2>/dev/null
  elif gf_have kdialog; then kdialog --inputbox "$1" "$2" 2>/dev/null
  else printf '%s [%s]: ' "$1" "$2" >&2; read -r a; printf '%s' "${a:-$2}"; fi
}

gf_need() { # $1=narzędzie $2=podpowiedź
  gf_have "$1" && return 0
  gf_err "Brak narzędzia '$1'. $2"
  exit 1
}

gf_is_ghostfs() { # exit 0 gdy ścieżka leży na ghostfs / fuse.ghostfs
  local t
  t="$(findmnt -no FSTYPE --target "$1" 2>/dev/null || true)"
  case "$t" in ghostfs|fuse.ghostfs) return 0;; *) return 1;; esac
}

gf_mountpoint() { findmnt -no TARGET --target "$1" 2>/dev/null; }

gf_open() { # otwórz katalog w menedżerze plików
  if gf_have thunar; then thunar "$1" &
  elif gf_have xdg-open; then xdg-open "$1" &
  fi
}
