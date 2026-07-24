# ghostfs Tools in Explorer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ghostfs filesystem operations (FUSE mount, snapshots, reflink copy, format) to the 1.x Thunar Explorer as right-click context-menu actions that invoke the bundled userspace ghostfs tools.

**Architecture:** UCA (Thunar custom actions) call small POSIX `sh` wrapper scripts. Wrappers detect ghostfs (via `findmnt`), pick the right ghostfs tool, and show dialogs (zenity→kdialog→terminal). Userspace ghostfs binaries are built from a pinned `quzopl/ghostfs-kernel` commit and bundled into the AppImage; wrappers and UCA actions are seeded like the existing "Open Terminal Here" action.

**Tech Stack:** POSIX shell, Thunar UCA (`uca.xml`), the existing patch/build/branding scripts, ghostfs-kernel userspace tools (C/GTK3/FUSE3), appimagetool.

## Global Constraints

- ghostfs-kernel pinned commit: **`35c29596ac6e`** (verbatim, used by `scripts/build-ghostfs.sh`).
- ghostfs userspace binaries and their names: `ghostfs-cli` (`make cli`→`build/ghostfs-cli`), `ghostfs` FUSE driver (`make fuse`→`build/ghostfs`, needs libfuse3), `ghostfs-snapshot-gui` (`tools/snapshot-gui`, GTK3), `ghostfs-disk-tool` (`tools/disk-tool`, GTK3).
- ghostfs-cli subcommands used: `format2 <c> <blocks>`, `snapshot <c> <name>`, `subvol-list <c>`, `subvol-del <c> <id>`, `df <c>`.
- Wrappers pass the file path as a **positional argument** (`"$1"`), never interpolated into a shell string (security: no command injection — same rule as the 2.x fix).
- Kernel module is **not** bundled; kernel-mount ioctl snapshots need it installed separately. FUSE mount + offline-cli snapshots + reflink work without it.
- Wrappers start with `set -eu`. Dialog fallback order: `zenity` → `kdialog` → terminal `read`.
- Bundled tools are found by bare name via `PATH`; AppRun exports `PATH="$APPDIR/usr/bin:$PATH"`; local build installs wrappers+binaries to `install/bin`.
- New patch number is **44** (highest existing is 43).
- Target branch: `master` (1.x line).

---

### Task 1: Build ghostfs userspace tools (`scripts/build-ghostfs.sh`)

**Files:**
- Create: `scripts/build-ghostfs.sh`
- Modify: `.gitignore` (add `dist-ghostfs/`, `.cache/ghostfs-kernel/`)
- Test: `scripts/build-ghostfs.sh` run + assertions (inline, below)

**Interfaces:**
- Produces: directory `dist-ghostfs/` containing executables `ghostfs-cli`, `ghostfs`, `ghostfs-snapshot-gui`, `ghostfs-disk-tool`. Consumed by Tasks 4 (local install) and 5 (AppImage bundle).

- [ ] **Step 1: Ensure build deps present**

Run:
```bash
pkg-config --exists gtk+-3.0 && echo gtk3-ok
dpkg -s libfuse3-dev >/dev/null 2>&1 || sudo apt-get install -y libfuse3-dev fuse3
```
Expected: `gtk3-ok`; libfuse3-dev installed.

- [ ] **Step 2: Write the failing test (assert the script produces 4 binaries)**

Create `scratchpad only` test command (not committed) — run after the script exists:
```bash
bash scripts/build-ghostfs.sh && for b in ghostfs-cli ghostfs ghostfs-snapshot-gui ghostfs-disk-tool; do
  test -x "dist-ghostfs/$b" || { echo "MISSING $b"; exit 1; }; done && echo ALL-4-OK
```
Expected now: FAIL (`scripts/build-ghostfs.sh: No such file`).

- [ ] **Step 3: Write `scripts/build-ghostfs.sh`**

```bash
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
  git clone https://github.com/quzopl/ghostfs-kernel "$SRC"
fi
git -C "$SRC" fetch --all --quiet || true
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
```

- [ ] **Step 4: Run the test**

Run:
```bash
chmod +x scripts/build-ghostfs.sh
bash scripts/build-ghostfs.sh && for b in ghostfs-cli ghostfs ghostfs-snapshot-gui ghostfs-disk-tool; do test -x "dist-ghostfs/$b" || { echo MISSING $b; exit 1; }; done && echo ALL-4-OK
```
Expected: `ALL-4-OK`. If `tools/disk-tool/ghostfs-disk-tool` name differs, read `tools/disk-tool/Makefile` for the actual output name and adjust the `install` line.

- [ ] **Step 5: Sanity-check the cli works (format a tiny container)**

Run:
```bash
T=$(mktemp -d); dist-ghostfs/ghostfs-cli format2 "$T/t.gfs" 16384 && dist-ghostfs/ghostfs-cli df "$T/t.gfs" && echo CLI-OK; rm -rf "$T"
```
Expected: df output + `CLI-OK`.

- [ ] **Step 6: Commit**

```bash
printf 'dist-ghostfs/\n.cache/ghostfs-kernel/\n' >> .gitignore
git add scripts/build-ghostfs.sh .gitignore
git commit -m "build: fetch+build ghostfs userspace tools (pinned 35c29596ac6e)"
```

---

### Task 2: Wrapper scripts (`branding/ghostfs/`)

**Files:**
- Create: `branding/ghostfs/gf-common.sh` (shared helpers, sourced)
- Create: `branding/ghostfs/gf-mount.sh`, `gf-umount.sh`, `gf-snap-gui.sh`, `gf-snap-vol.sh`, `gf-disk.sh`, `gf-reflink.sh`
- Test: `branding/ghostfs/test-wrappers.sh`

**Interfaces:**
- Consumes: `dist-ghostfs/` binaries on PATH (Task 1) at runtime.
- Produces: executable wrappers invoked by UCA (Task 3) as `gf-<name>.sh "<path>"`. `gf-common.sh` exposes: `gf_have <tool>`, `gf_need <tool> <hint>`, `gf_err <msg>`, `gf_entry <title> <default>` (prints entered text), `gf_is_ghostfs <path>` (exit 0 if on ghostfs), `gf_mountpoint <path>` (prints mount target), `gf_open <path>` (opens in file manager).

- [ ] **Step 1: Write the failing test**

Create `branding/ghostfs/test-wrappers.sh`:
```bash
#!/usr/bin/env bash
set -u
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$PWD/dist-ghostfs:$PATH"
. "$HERE/gf-common.sh"
fail=0
# gf_is_ghostfs: a normal /tmp dir is NOT ghostfs
if gf_is_ghostfs /tmp 2>/dev/null; then echo "FAIL: /tmp reported as ghostfs"; fail=1; else echo "ok: /tmp not ghostfs"; fi
# gf-reflink on a plain-FS file: must fail loudly (no CoW), not silently copy
T=$(mktemp -d); echo x > "$T/a"; 
if GF_NONINTERACTIVE=1 "$HERE/gf-reflink.sh" "$T/a" 2>/dev/null; then echo "FAIL: reflink 'succeeded' on non-CoW"; fail=1; else echo "ok: reflink refused on non-CoW"; fi
rm -rf "$T"
[ "$fail" = 0 ] && echo "WRAPPERS-OK" || { echo "WRAPPERS-FAIL"; exit 1; }
```
Run: `bash branding/ghostfs/test-wrappers.sh`
Expected now: FAIL (`gf-common.sh: No such file`).

- [ ] **Step 2: Write `branding/ghostfs/gf-common.sh`**

```bash
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
```

- [ ] **Step 3: Write `branding/ghostfs/gf-reflink.sh`**

```bash
#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
f="$1"
dst="$(dirname "$f")/$(basename "$f") (reflink)"
if cp --reflink=always -- "$f" "$dst" 2>/dev/null; then
  [ "${GF_NONINTERACTIVE:-}" = 1 ] || gf_info "Utworzono reflink: $(basename "$dst")"
else
  gf_err "Reflink niedostępny — plik nie leży na wolumenie ghostfs/CoW."
  exit 1
fi
```

- [ ] **Step 4: Write the remaining wrappers**

`branding/ghostfs/gf-mount.sh`:
```bash
#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
gf_need ghostfs "Zainstaluj/zbuduj ghostfs (sterownik FUSE)."
c="$1"
name="$(basename "$c" .gfs)"
mp="${XDG_DATA_HOME:-$HOME/.local/share}/ghostfs-mounts/$name"
if findmnt -no TARGET "$mp" >/dev/null 2>&1; then gf_open "$mp"; exit 0; fi
mkdir -p "$mp"
if ghostfs "$c" "$mp"; then gf_open "$mp"; else gf_err "Montowanie FUSE nie powiodło się."; rmdir "$mp" 2>/dev/null || true; exit 1; fi
```

`branding/ghostfs/gf-umount.sh`:
```bash
#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
c="$1"
name="$(basename "$c" .gfs)"
mp="${XDG_DATA_HOME:-$HOME/.local/share}/ghostfs-mounts/$name"
if findmnt -no TARGET "$mp" >/dev/null 2>&1; then
  fusermount3 -u "$mp" 2>/dev/null || fusermount -u "$mp"
  rmdir "$mp" 2>/dev/null || true
  gf_info "Odmontowano $name."
else
  gf_err "Kontener nie jest zamontowany."
  exit 1
fi
```

`branding/ghostfs/gf-snap-gui.sh` (kontener .gfs, offline):
```bash
#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
gf_need ghostfs-snapshot-gui "Zbuduj tools/snapshot-gui z ghostfs-kernel."
exec ghostfs-snapshot-gui "$1"
```

`branding/ghostfs/gf-snap-vol.sh` (folder na zamontowanym ghostfs):
```bash
#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
gf_need ghostfs-snapshot-gui "Zbuduj tools/snapshot-gui z ghostfs-kernel."
if ! gf_is_ghostfs "$1"; then gf_err "To nie jest wolumen ghostfs."; exit 1; fi
mp="$(gf_mountpoint "$1")"
exec ghostfs-snapshot-gui "$mp"
```

`branding/ghostfs/gf-disk.sh`:
```bash
#!/usr/bin/env sh
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
. "$HERE/gf-common.sh"
gf_need ghostfs-disk-tool "Zbuduj tools/disk-tool z ghostfs-kernel."
exec ghostfs-disk-tool "$1"
```

- [ ] **Step 5: Run the test**

Run:
```bash
chmod +x branding/ghostfs/*.sh
bash branding/ghostfs/test-wrappers.sh
```
Expected: `ok: /tmp not ghostfs`, `ok: reflink refused on non-CoW`, `WRAPPERS-OK`.

- [ ] **Step 6: Verify reflink SUCCEEDS on a real ghostfs (best-effort; skip if FUSE unavailable)**

Run:
```bash
export PATH="$PWD/dist-ghostfs:$PATH"; T=$(mktemp -d)
ghostfs-cli format2 "$T/v.gfs" 16384
mp="$T/mnt"; mkdir -p "$mp"
if ghostfs "$T/v.gfs" "$mp" 2>/dev/null; then
  echo hello > "$mp/f"; branding/ghostfs/gf-reflink.sh "$mp/f" && test -f "$mp/f (reflink)" && echo REFLINK-OK
  fusermount3 -u "$mp" 2>/dev/null || fusermount -u "$mp"
else echo "SKIP: FUSE niedostępny w tym środowisku"; fi
rm -rf "$T"
```
Expected: `REFLINK-OK` (or `SKIP` if the sandbox forbids FUSE — acceptable, offline path is the hard gate).

- [ ] **Step 7: Commit**

```bash
git add branding/ghostfs/
git commit -m "feat: ghostfs wrapper scripts (mount/umount/snapshots/reflink/disk)"
```

---

### Task 3: UCA actions patch (`patches/44-ghostfs-actions.patch`)

**Files:**
- Create: `patches/44-ghostfs-actions.patch`
- Test: apply full patch series to a pristine Thunar tree; validate XML.

**Interfaces:**
- Consumes: wrappers `gf-*.sh` on PATH (Tasks 2, 4, 5) at action-run time.
- Produces: `<action>` entries in the installed `uca.xml` template. Consumed by Task 4 (seeding logic must match these action `<name>`s: "ghostfs: Zamontuj (FUSE)", "ghostfs: Odmontuj", "ghostfs: Snapshoty…", "ghostfs: Formatuj / zarządzaj", "ghostfs: Snapshoty tego wolumenu…", "ghostfs: Kopiuj jako reflink").

- [ ] **Step 1: Fetch + patch a pristine tree**

Run:
```bash
bash scripts/fetch-sources.sh
cp thunar-src/plugins/thunar-uca/uca.xml.in /tmp/uca.orig
bash scripts/apply-patches.sh   # applies 01..43
```
Expected: patches apply cleanly.

- [ ] **Step 2: Add the ghostfs actions to `uca.xml.in`**

Edit `thunar-src/plugins/thunar-uca/uca.xml.in`: immediately before the closing `</actions>`, insert:
```xml
  <action>
    <icon>drive-harddisk</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Zamontuj (FUSE)</name>
    <command>gf-mount.sh %f</command>
    <description>Zamontuj kontener ghostfs przez FUSE</description>
    <startup-notify/>
    <other-files/>
  </action>
  <action>
    <icon>media-eject</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Odmontuj</name>
    <command>gf-umount.sh %f</command>
    <description>Odmontuj wolumen ghostfs</description>
    <other-files/>
  </action>
  <action>
    <icon>document-open-recent</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Snapshoty…</name>
    <command>gf-snap-gui.sh %f</command>
    <description>Zarządzaj snapshotami kontenera ghostfs</description>
    <other-files/>
  </action>
  <action>
    <icon>drive-removable-media</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Formatuj / zarządzaj</name>
    <command>gf-disk.sh %f</command>
    <description>Formatuj/zarządzaj wolumenem ghostfs (disk-tool)</description>
    <other-files/>
  </action>
  <action>
    <icon>document-open-recent</icon>
    <patterns>*</patterns>
    <name>ghostfs: Snapshoty tego wolumenu…</name>
    <command>gf-snap-vol.sh %f</command>
    <description>Snapshoty zamontowanego wolumenu ghostfs</description>
    <directories/>
  </action>
  <action>
    <icon>edit-copy</icon>
    <patterns>*</patterns>
    <name>ghostfs: Kopiuj jako reflink</name>
    <command>gf-reflink.sh %f</command>
    <description>Klon CoW (reflink) w obrębie wolumenu ghostfs</description>
    <other-files/>
    <text-files/>
    <image-files/>
    <audio-files/>
    <video-files/>
  </action>

</actions>
```
(Replace the existing final `</actions>` line — do not duplicate it.)

- [ ] **Step 3: Validate XML and generate the patch**

Run:
```bash
python3 -c "import xml.dom.minidom;xml.dom.minidom.parse('thunar-src/plugins/thunar-uca/uca.xml.in');print('XML OK')"
diff -u /tmp/uca.orig thunar-src/plugins/thunar-uca/uca.xml.in > patches/44-ghostfs-actions.patch || true
head -1 patches/44-ghostfs-actions.patch
```
Expected: `XML OK`; patch file non-empty. Fix the patch header paths to `--- plugins/thunar-uca/uca.xml.in` / `+++ plugins/thunar-uca/uca.xml.in` so it applies with `patch -p0 -d thunar-src` (match the format of existing patches like `patches/29-run-in-terminal.patch`).

- [ ] **Step 4: Verify the full series still applies to a pristine tree**

Run:
```bash
rm -rf /tmp/vt && mkdir -p /tmp/vt && tar -xjf .cache/thunar-4.20.8.tar.bz2 -C /tmp/vt --strip-components=1
ok=1; for p in patches/*.patch; do patch -p0 -N -d /tmp/vt < "$p" >/dev/null 2>&1 || { echo "FAIL $p"; ok=0; }; done
[ "$ok" = 1 ] && python3 -c "import xml.dom.minidom;xml.dom.minidom.parse('/tmp/vt/plugins/thunar-uca/uca.xml.in');print('44 patches clean + XML OK')"
```
Expected: `44 patches clean + XML OK`.

- [ ] **Step 5: Commit**

```bash
git add patches/44-ghostfs-actions.patch
git commit -m "feat: patch 44 — ghostfs actions in Thunar context menu (uca.xml)"
```

---

### Task 4: Local install + uca seeding (`scripts/install-branding.sh`)

**Files:**
- Modify: `scripts/install-branding.sh`
- Test: run in an isolated `HOME`; assert wrappers installed + uca.xml seeded + valid.

**Interfaces:**
- Consumes: `dist-ghostfs/` (Task 1), `branding/ghostfs/*.sh` (Task 2), action `<name>`s from Task 3.
- Produces: `install/bin/gf-*.sh`, `install/bin/ghostfs*` symlinks/copies, and `~/.config/Thunar/uca.xml` containing the ghostfs actions (idempotent).

- [ ] **Step 1: Write the failing test**

Run (after editing the script):
```bash
SPT=$(mktemp -d); rm -rf dist-ghostfs || true; bash scripts/build-ghostfs.sh >/dev/null
HOME="$SPT" XDG_CONFIG_HOME="$SPT/.config" XDG_DATA_HOME="$SPT/.local/share" bash scripts/install-branding.sh >/dev/null 2>&1
test -x install/bin/gf-mount.sh && grep -q 'ghostfs: Zamontuj' "$SPT/.config/Thunar/uca.xml" && python3 -c "import xml.dom.minidom;xml.dom.minidom.parse('$SPT/.config/Thunar/uca.xml')" && echo SEED-OK; rm -rf "$SPT"
```
Expected now: FAIL (script doesn't install ghostfs bits yet).

- [ ] **Step 2: Install wrappers + binaries in `install-branding.sh`**

Add after the existing font/icon install block (before the uca.xml migration block), guarded so it works even if `dist-ghostfs/` is absent:
```bash
# narzędzia ghostfs: owijki + (jeśli zbudowane) binarki userspace do install/bin
mkdir -p "$PREFIX/bin"
install -m755 branding/ghostfs/gf-*.sh "$PREFIX/bin/" 2>/dev/null || true
install -m644 branding/ghostfs/gf-common.sh "$PREFIX/bin/" 2>/dev/null || true
if [ -d dist-ghostfs ]; then
  for b in ghostfs-cli ghostfs ghostfs-snapshot-gui ghostfs-disk-tool; do
    [ -x "dist-ghostfs/$b" ] && install -m755 "dist-ghostfs/$b" "$PREFIX/bin/"
  done
fi
```

- [ ] **Step 3: Seed ghostfs actions into the user uca.xml (idempotent)**

In the existing `UCA_FILE="$UCA" python3 - <<'PYEOF'` block, extend the migration Python so it appends the six ghostfs actions before `</actions>` when absent. Add, right after the "Open in Terminal" injection logic:
```python
gf_actions = '''  <action>
    <icon>drive-harddisk</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Zamontuj (FUSE)</name>
    <command>gf-mount.sh %f</command>
    <description>Zamontuj kontener ghostfs przez FUSE</description>
    <startup-notify/>
    <other-files/>
  </action>
  <action>
    <icon>media-eject</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Odmontuj</name>
    <command>gf-umount.sh %f</command>
    <description>Odmontuj wolumen ghostfs</description>
    <other-files/>
  </action>
  <action>
    <icon>document-open-recent</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Snapshoty…</name>
    <command>gf-snap-gui.sh %f</command>
    <description>Zarządzaj snapshotami kontenera ghostfs</description>
    <other-files/>
  </action>
  <action>
    <icon>drive-removable-media</icon>
    <patterns>*.gfs</patterns>
    <name>ghostfs: Formatuj / zarządzaj</name>
    <command>gf-disk.sh %f</command>
    <description>Formatuj/zarządzaj wolumenem ghostfs (disk-tool)</description>
    <other-files/>
  </action>
  <action>
    <icon>document-open-recent</icon>
    <patterns>*</patterns>
    <name>ghostfs: Snapshoty tego wolumenu…</name>
    <command>gf-snap-vol.sh %f</command>
    <description>Snapshoty zamontowanego wolumenu ghostfs</description>
    <directories/>
  </action>
  <action>
    <icon>edit-copy</icon>
    <patterns>*</patterns>
    <name>ghostfs: Kopiuj jako reflink</name>
    <command>gf-reflink.sh %f</command>
    <description>Klon CoW (reflink) w obrębie wolumenu ghostfs</description>
    <other-files/>
    <text-files/>
    <image-files/>
    <audio-files/>
    <video-files/>
  </action>
'''
if '<name>ghostfs: Zamontuj (FUSE)</name>' not in out and '</actions>' in out:
    out = out.replace('</actions>', gf_actions + '</actions>')
```

- [ ] **Step 4: Run the test**

Run the Step-1 command again.
Expected: `SEED-OK`.

- [ ] **Step 5: Idempotency check (second run must not duplicate)**

Run:
```bash
SPT=$(mktemp -d)
for i in 1 2; do HOME="$SPT" XDG_CONFIG_HOME="$SPT/.config" XDG_DATA_HOME="$SPT/.local/share" bash scripts/install-branding.sh >/dev/null 2>&1; done
n=$(grep -c 'ghostfs: Zamontuj' "$SPT/.config/Thunar/uca.xml"); echo "wystąpień: $n"; test "$n" = 1 && echo IDEMPOTENT-OK; rm -rf "$SPT"
```
Expected: `wystąpień: 1`, `IDEMPOTENT-OK`.

- [ ] **Step 6: Commit**

```bash
git add scripts/install-branding.sh
git commit -m "feat: install ghostfs wrappers/binaries and seed uca.xml actions"
```

---

### Task 5: Bundle into AppImage (`scripts/build-appimage.sh`)

**Files:**
- Modify: `scripts/build-appimage.sh`
- Test: build AppImage; assert binaries+wrappers bundled and PATH wired; scrubbed-env smoke.

**Interfaces:**
- Consumes: `dist-ghostfs/` (Task 1), `branding/ghostfs/*.sh` (Task 2).
- Produces: `AppDir/usr/bin/{ghostfs-cli,ghostfs,ghostfs-snapshot-gui,ghostfs-disk-tool,gf-*.sh,gf-common.sh}`; `AppRun` exports `PATH="$APPDIR/usr/bin:$PATH"`.

- [ ] **Step 1: Ensure ghostfs tools are built before packaging**

In `build-appimage.sh`, near the top (after `cd` to repo root, before the AppImage assembly), add:
```bash
# zbuduj narzędzia ghostfs, jeśli brak
[ -x dist-ghostfs/ghostfs-cli ] || bash scripts/build-ghostfs.sh
```

- [ ] **Step 2: Copy ghostfs binaries + wrappers into AppDir**

After the block that installs the app icon/themes into `$AD`, add:
```bash
# narzędzia ghostfs (userspace) + owijki
mkdir -p "$AD/usr/bin"
for b in ghostfs-cli ghostfs ghostfs-snapshot-gui ghostfs-disk-tool; do
  install -m755 "dist-ghostfs/$b" "$AD/usr/bin/$b"
done
install -m755 branding/ghostfs/gf-*.sh "$AD/usr/bin/"
install -m644 branding/ghostfs/gf-common.sh "$AD/usr/bin/"
```
Then extend the ldd-closure gathering (the existing loop that runs `gather` over seed ELFs) to also cover the ghostfs binaries so their shared libs (libfuse3, libgtk-3) are bundled:
```bash
for so in "$AD"/usr/bin/ghostfs "$AD"/usr/bin/ghostfs-cli \
          "$AD"/usr/bin/ghostfs-snapshot-gui "$AD"/usr/bin/ghostfs-disk-tool; do
  [ -x "$so" ] && SEEDS+=("$so")
done
```
(Place this addition before the `for s in "${SEEDS[@]}"; do gather "$s"; done` line.)

- [ ] **Step 3: Wire PATH in AppRun**

In the AppRun heredoc, add near the other `export` lines:
```bash
export PATH="$APPDIR/usr/bin:${PATH:-/usr/bin:/bin}"
```

- [ ] **Step 4: Seed ghostfs actions from the AppImage too**

The AppImage already seeds `uca.xml` via an AppRun hook (from the 2.x-era `explorer-uca-setup.sh` on 1.x it is the install-branding-equivalent). On the 1.x line, the uca seeding runs in `install-branding.sh` only. Add an AppRun-time seeding step: create `"$AD/usr/bin/explorer-ghostfs-seed.sh"` that appends the six actions to `~/.config/Thunar/uca.xml` if absent (reuse the exact Python from Task 4 Step 3, reading `$HOME`), and call it from AppRun before `exec`:
```bash
sh "$APPDIR/usr/bin/explorer-ghostfs-seed.sh" 2>/dev/null || true
```
Write `explorer-ghostfs-seed.sh` as a self-contained POSIX script that runs the same idempotent Python append against `${XDG_CONFIG_HOME:-$HOME/.config}/Thunar/uca.xml` (seed the template first if the file is absent, mirroring the existing terminal-action seeding).

- [ ] **Step 5: Build and assert bundling**

Run:
```bash
SP_PKG="$PWD/deps/prefix/lib/pkgconfig"; export PKG_CONFIG_PATH="$SP_PKG" LD_LIBRARY_PATH="$PWD/deps/prefix/lib"
rm -rf AppDir; bash scripts/build-appimage.sh 2>&1 | tail -3
cd /tmp && rm -rf aicheck && mkdir aicheck && cd aicheck
/home/ubuntu/explorer/explorer-thunar/dist/Explorer-x86_64.AppImage --appimage-extract >/dev/null 2>&1
for b in ghostfs-cli ghostfs ghostfs-snapshot-gui ghostfs-disk-tool gf-mount.sh gf-reflink.sh; do
  test -e "squashfs-root/usr/bin/$b" || { echo "MISSING $b"; exit 1; }; done && echo BUNDLE-OK
grep -q 'PATH="$APPDIR/usr/bin' squashfs-root/AppRun && echo PATH-OK
cd /home/ubuntu/explorer/explorer-thunar
```
Expected: `BUNDLE-OK`, `PATH-OK`.

- [ ] **Step 6: Scrubbed-env smoke — bundled ghostfs-cli runs**

Run:
```bash
cat > /tmp/gf-smoke.sh <<'S'
#!/bin/bash
unset LD_LIBRARY_PATH GI_TYPELIB_PATH
D=$(mktemp -d)
/tmp/aicheck/squashfs-root/usr/bin/ghostfs-cli format2 "$D/x.gfs" 16384 && echo GF-CLI-BUNDLED-OK
rm -rf "$D"
S
bash /tmp/gf-smoke.sh
```
Expected: `GF-CLI-BUNDLED-OK` (bundled binary runs with its bundled libs). If it needs a lib in `usr/lib`, confirm Step 2's ldd closure added it; rebuild.

- [ ] **Step 7: Commit**

```bash
git add scripts/build-appimage.sh
git commit -m "build: bundle ghostfs tools + wrappers into the AppImage, wire PATH, seed uca"
```

---

### Task 6: README + end-to-end verification

**Files:**
- Modify: `README.md`
- Test: context-menu screenshot (Xvfb) + full offline flow.

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Document the feature in README**

Add a "ghostfs tools" bullet under Features and a short section: right-click a `.gfs` container → Mount (FUSE) / Snapshots / Format; right-click a folder on a mounted ghostfs → Snapshots; right-click a file → Copy as reflink. Note the kernel-module caveat (online kernel-mount snapshots need `insmod ghostfs_km.ko` + root; FUSE mount, offline snapshots and reflink work without it). Note tools are bundled in the AppImage.

- [ ] **Step 2: End-to-end offline flow (hard gate — no FUSE needed)**

Run:
```bash
export PATH="$PWD/dist-ghostfs:$PWD/branding/ghostfs:$PATH"
T=$(mktemp -d); ghostfs-cli format2 "$T/v.gfs" 16384
ghostfs-cli snapshot "$T/v.gfs" snap1
ghostfs-cli subvol-list "$T/v.gfs" | grep -q snap1 && echo SNAP-CREATED
id=$(ghostfs-cli subvol-list "$T/v.gfs" | awk '/snap1/{print $1; exit}')
ghostfs-cli subvol-del "$T/v.gfs" "$id" && ghostfs-cli subvol-list "$T/v.gfs" | grep -qv snap1 && echo SNAP-DELETED
rm -rf "$T"
```
Expected: `SNAP-CREATED`, `SNAP-DELETED`. (If `subvol-list` column layout differs, adjust the `awk`; read `ghostfs-cli subvol-list` output format first.)

- [ ] **Step 3: Context-menu screenshot (Xvfb)**

Run the existing screenshot recipe (seed a demo HOME, install-branding, launch `install/bin/explorer` under Xvfb, right-click a `*.gfs` file), capture the menu, and confirm the "ghostfs: …" entries are visible. Save to `docs/screenshots/` only if using fake data.

- [ ] **Step 4: Full 44-patch clean-apply re-check**

Run:
```bash
bash scripts/fetch-sources.sh >/dev/null 2>&1
rm -rf /tmp/vt2 && mkdir -p /tmp/vt2 && tar -xjf .cache/thunar-4.20.8.tar.bz2 -C /tmp/vt2 --strip-components=1
ok=1; for p in patches/*.patch; do patch -p0 -N -d /tmp/vt2 < "$p" >/dev/null 2>&1 || { echo FAIL $p; ok=0; }; done
[ "$ok" = 1 ] && echo "ALL PATCHES CLEAN"
```
Expected: `ALL PATCHES CLEAN`.

- [ ] **Step 5: Commit + tag + release**

```bash
git add README.md
git commit -m "docs: ghostfs tools in Explorer; end-to-end verified"
git tag -a v1.3.0 -m "Explorer 1.3.0 — ghostfs filesystem tools (snapshots, reflink, FUSE mount, format)"
# push master + tag; build AppImage; gh release create v1.3.0 with the AppImage
```
Expected: v1.3.0 released; because 1.3.0 > 1.2.13, the in-app updater will offer it to existing 1.x users (intended).

---

## Self-Review

**Spec coverage:** §1 context → Task 1 (tools) + Global Constraints. §2 components → Tasks 1–5 (each file mapped). §3 actions/UX → Task 3 (UCA) + Task 2 (wrappers) + Task 2's dialog fallback. §4 bundling → Task 5 + Task 1. §5 resilience → Task 2 (`set -eu`, guards, gf_err) + tests in Tasks 2/4. §6 tests → Tasks 2/4/5/6. §7 out-of-scope respected (no thunarx plugin, no configurable path, no in-window panel, no 2.x). Covered.

**Placeholder scan:** wrapper code, patch XML, seeding Python, and test commands are all concrete. The only deferred detail is exact `subvol-list` column parsing (Task 6 Step 2) and the disk-tool binary name (Task 1 Step 4) — both flagged with a "read the actual output/Makefile and adjust" instruction rather than left vague, because they depend on ghostfs-kernel output this plan can't see without building. Acceptable.

**Type consistency:** wrapper filenames (`gf-mount.sh`, `gf-umount.sh`, `gf-snap-gui.sh`, `gf-snap-vol.sh`, `gf-disk.sh`, `gf-reflink.sh`, `gf-common.sh`) and action `<name>`s are identical across Tasks 2, 3, 4, 5. `gf_common.sh` helper names (`gf_have/gf_need/gf_err/gf_info/gf_entry/gf_is_ghostfs/gf_mountpoint/gf_open`) are used consistently. ghostfs binary names match Task 1's output and Global Constraints.
