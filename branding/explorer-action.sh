#!/bin/sh
# Explorer's own right-click actions (uca.xml): explorer-action.sh <action> <file>...

notify() { notify-send -a Explorer -i system-file-manager "$1" "$2" 2>/dev/null || true; }

copy_text() {
  if command -v wl-copy >/dev/null 2>&1 && [ -n "$WAYLAND_DISPLAY" ]; then
    printf '%s' "$1" | wl-copy
  elif command -v xclip >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
    printf '%s' "$1" | xclip -selection clipboard
  elif command -v xsel >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
    printf '%s' "$1" | xsel --clipboard --input
  else
    # KDE without a clipboard tool: Klipper takes it over D-Bus
    gdbus call --session --dest org.kde.klipper --object-path /klipper \
      --method org.kde.klipper.klipper.setClipboardContents "$1" >/dev/null 2>&1
  fi
}

show_text() { # title, text
  if command -v zenity >/dev/null 2>&1; then
    printf '%s\n' "$2" | zenity --text-info --title="$1" --width=760 --height=420 --font=monospace 2>/dev/null
  elif command -v kdialog >/dev/null 2>&1; then
    kdialog --title "$1" --msgbox "$2"
  else
    notify "$1" "$2"
  fi
}

action="$1"; shift
case "$action" in
  copy-path)
    paths=$(printf '%s\n' "$@")
    if copy_text "$paths"; then
      [ $# -eq 1 ] && notify "Path copied" "$1" || notify "Paths copied" "$# items"
    else
      notify "Could not copy the path" "Install wl-clipboard or xclip."
    fi ;;
  checksum)
    out=$(sha256sum -- "$@" 2>&1)
    copy_text "$(printf '%s\n' "$out" | cut -d' ' -f1)" 2>/dev/null
    show_text "SHA-256 (copied to the clipboard)" "$out" ;;
  compare)
    [ $# -eq 2 ] || { notify "Compare Files" "Select exactly two files."; exit 1; }
    for tool in meld kompare kdiff3; do
      command -v "$tool" >/dev/null 2>&1 && exec "$tool" "$1" "$2"
    done
    out=$(diff -u -- "$1" "$2")
    [ -n "$out" ] || out="The files are identical."
    show_text "Compare: $(basename "$1") ↔ $(basename "$2")" "$out" ;;
  send-phone)
    command -v kdeconnect-handler >/dev/null 2>&1 || { notify "Send to Phone" "KDE Connect is not installed."; exit 1; }
    for f in "$@"; do kdeconnect-handler "$f"; done ;;
  *)
    echo "usage: explorer-action.sh copy-path|checksum|compare|send-phone FILE..." >&2
    exit 2 ;;
esac
