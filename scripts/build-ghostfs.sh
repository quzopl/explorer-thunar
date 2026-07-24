#!/usr/bin/env bash
# Buduje narzędzia userspace ghostfs (z przypiętego commita) do dist-ghostfs/.
# Wymaga: gcc, make, git, pkg-config, libgtk-3-dev, libfuse3-dev.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
PIN="35c29596ac6e"
SRC="$ROOT/.cache/ghostfs-kernel"
OUT="$ROOT/dist-ghostfs"

if [ ! -d "$SRC/.git" ]; then
  # ghostfs-kernel jest PRYWATNE — wymaga autoryzacji. Kolejność:
  # GH_TOKEN (CI/nasz build) -> istniejące poświadczenia git użytkownika.
  if [ -n "${GH_TOKEN:-}" ]; then
    git clone "https://x-access-token:${GH_TOKEN}@github.com/quzopl/ghostfs-kernel" "$SRC"
  elif git clone "https://github.com/quzopl/ghostfs-kernel" "$SRC" 2>/dev/null; then
    :
  else
    echo "BŁĄD: nie udało się sklonować prywatnego ghostfs-kernel." >&2
    echo "Ustaw GH_TOKEN (repo scope) lub skonfiguruj poświadczenia git dla github.com." >&2
    exit 1
  fi
fi
git -C "$SRC" fetch --all --quiet 2>/dev/null || true
git -C "$SRC" checkout --quiet "$PIN"

make -C "$SRC" cli
make -C "$SRC" fuse
make -C "$SRC/tools/snapshot-gui"
make -C "$SRC/tools/disk-tool"

rm -rf "$OUT"; mkdir -p "$OUT"
install -m755 "$SRC/build/ghostfs-cli"                     "$OUT/ghostfs-cli"
install -m755 "$SRC/build/ghostfs"                         "$OUT/ghostfs"
install -m755 "$SRC/tools/snapshot-gui/ghostfs-snapshot-gui" "$OUT/ghostfs-snapshot-gui"
install -m755 "$SRC/tools/disk-tool/ghostfs-disk-tool"       "$OUT/ghostfs-disk-tool"
echo "OK: dist-ghostfs/ (ghostfs-cli, ghostfs, ghostfs-snapshot-gui, ghostfs-disk-tool)"
