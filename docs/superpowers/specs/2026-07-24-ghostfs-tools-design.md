# Explorer ↔ ghostfs — narzędzia systemu plików w menu kontekstowym

**Data:** 2026-07-24
**Linia:** 1.x (Explorer na Thunarze, GTK3) — renderuje się zdalnie (ThinLinc), główna linia użytkownika.
**Cel:** wpiąć operacje ghostfs (snapshoty, reflink, montowanie kontenerów, format) w menu
kontekstowe Explorera, wołając bundlowane narzędzia userspace z [`quzopl/ghostfs-kernel`].

## 1. Kontekst

`ghostfs` to natywny CoW B-tree FS z snapshotami, reflinkiem (`FICLONE`), subwolumenami,
szyfrowaniem i kompresją. Dostępne interfejsy (przypięty commit **`35c29596ac6e`**):

- **`ghostfs-cli`** — offline (kontener `.gfs`): `snapshot <c> <name>`, `subvol-list <c>`,
  `subvol-del <c> <id>`, `rollback`, `format2`, `df`, `fsck`.
- **`ghostfs` (FUSE)** — montowanie kontenera w userspace, bez root/modułu jądra.
- **ioctl-e jądra** (`GHOSTFS_IOC_SNAPSHOT` / `SUBVOL_LIST` / `SNAP_DELETE`) — snapshoty
  *zamontowanego kernelowego* wolumenu; wymagają modułu jądra + root.
- **`ghostfs-snapshot-gui`** (GTK3) — obsługuje oba tryby (ioctl online / cli offline).
- **`disk-tool`** (GTK3) — format, kompresja, szyfrowanie, GPT.
- **reflink** = `cp --reflink=always` (coreutils, przez FICLONE) — bez narzędzi ghostfs.

Explorer **nie reimplementuje** operacji — wywołuje powyższe. Integracja przez akcje **UCA**
(jak istniejąca „Open Terminal Here"), bez nowej wtyczki C.

## 2. Komponenty (repo explorer-thunar)

| Element | Rola |
|---|---|
| `patches/44-ghostfs-actions.patch` | rozszerza szablon `plugins/thunar-uca/uca.xml.in` o akcje ghostfs (na wzór akcji terminala) |
| `branding/ghostfs/*.sh` | owijki POSIX `sh`, jedna na akcję: wykrycie ghostfs, wywołanie komendy, dialogi/błędy |
| `scripts/build-ghostfs.sh` | klonuje ghostfs-kernel @ `35c29596ac6e`, buduje userspace (`make cli fuse`, `tools/snapshot-gui`, `tools/disk-tool`), zbiera binarki do `dist-ghostfs/` |
| `scripts/build-appimage.sh` (zmiana) | bundluje binarki ghostfs + owijki do `AppDir/usr/bin`; AppRun dokłada `$APPDIR/usr/bin` do `PATH` |
| `scripts/install-branding.sh` (zmiana) | instaluje owijki lokalnie i zasiewa akcje ghostfs do `~/.config/Thunar/uca.xml` (idempotentnie) |

Owijki wołane po nazwie (`ghostfs-cli`, `ghostfs`, `ghostfs-snapshot-gui`, `disk-tool`) — muszą być
w `PATH` środowiska, w którym Thunar odpala akcję. AppRun to gwarantuje w AppImage; lokalnie
`install-branding` kładzie je do `install/bin`.

## 3. Akcje UCA i UX

Dialogi: **zenity → kdialog → terminal** (`read`) jako fallback (nie bundlujemy zenity).

### Na pliku `*.gfs` (`<patterns>*.gfs</patterns>`, `<other-files/>`)
- **ghostfs: Zamontuj (FUSE)** — `gf-mount.sh`: tworzy punkt `~/.local/share/ghostfs-mounts/<nazwa>`,
  `ghostfs <plik> <punkt>`, otwiera folder w Explorerze. Idempotentnie (gdy już zamontowany — otwiera).
- **ghostfs: Odmontuj** — `gf-umount.sh`: `fusermount3 -u <punkt>` jeśli zamontowany.
- **ghostfs: Snapshoty…** — `gf-snap-gui.sh`: `ghostfs-snapshot-gui <plik>` (offline).
- **ghostfs: Formatuj / zarządzaj** — `gf-disk.sh`: `disk-tool <plik>`.

### Na folderze (`<directories/>`, guard w owijce)
- **ghostfs: Snapshoty tego wolumenu…** — `gf-snap-vol.sh`: sprawdza w `/proc/mounts`, czy ścieżka
  leży na FS typu `ghostfs`/`fuse.ghostfs`; jeśli tak → wyznacza punkt montowania i uruchamia
  `ghostfs-snapshot-gui <punkt>` (Twoje GUI samo rozstrzyga tryb online-ioctl vs offline-cli i ma
  dialog „Nowy snapshot" do tworzenia + listę/usuwanie); jeśli nie → dialog „to nie jest wolumen
  ghostfs".

  *Uwaga (usuwa niejednoznaczność):* Explorer nie decyduje o trybie online/offline ani nie tworzy
  snapshotu sam — deleguje w całości do `ghostfs-snapshot-gui`, które ten wybór już implementuje.
  Owijka odpowiada wyłącznie za guard (czy to ghostfs) i wskazanie właściwego celu.

### Na pliku (`<other-files/>`, `<text-files/>`, `<image-files/>`…)
- **ghostfs: Kopiuj jako reflink** — `gf-reflink.sh`: `cp --reflink=always %f "<dest>"` (domyślnie
  `<nazwa> (reflink)`); przy niepowodzeniu (nie-CoW FS) → jasny komunikat.

Wszystkie akcje: `%f` przekazywane jako **argument pozycyjny** owijce (nie wklejane w łańcuch
powłoki) — zgodnie z lekcją bezpieczeństwa z 2.x (command injection).

## 4. Bundlowanie

- `build-ghostfs.sh` przypina commit, cache pobrania w `.cache/`, wynik w `dist-ghostfs/` (git-ignored).
- `build-appimage.sh`: `install -m755 dist-ghostfs/* "$AD/usr/bin/"` + owijki; AppRun już eksportuje
  środowisko — dodać `export PATH="$APPDIR/usr/bin:$PATH"`.
- **Ograniczenie (udokumentowane w README):** moduł jądra nie jest bundlowany; snapshoty
  zamontowanego kernelowego wolumenu wymagają `insmod ghostfs_km.ko` + root. FUSE-mount, snapshoty
  offline, format i reflink działają bez modułu.

## 5. Odporność

- Owijka bez wymaganego narzędzia → dialog z podpowiedzią (co doinstalować / że to build bez ghostfs).
- Reflink poza CoW-FS → komunikat, brak cichego zwykłego kopiowania.
- Montowanie: nie nadpisuje istniejącego punktu; odmontowanie tylko gdy faktycznie zamontowane.
- `set -eu` w owijkach; brak stanów pośrednich.

## 6. Testy (izolowane środowisko)

1. `build-ghostfs.sh` → binarki w `dist-ghostfs/`.
2. `ghostfs-cli format2 t.gfs 16384`; FUSE-mount przez `gf-mount.sh`; utwórz plik.
3. `gf-snap-create.sh` / `ghostfs-cli snapshot` → `subvol-list` pokazuje snapshot; `subvol-del` usuwa.
4. `gf-reflink.sh` na pliku → kopia istnieje; `ghostfs-cli df` potwierdza brak podwojenia miejsca.
5. Zrzut menu kontekstowego Thunara z pozycjami „ghostfs: …" (Xvfb).

## 7. Poza zakresem (YAGNI)

- Wtyczka thunarx w C (kontekstowe menu) — świadomie pominięta na rzecz UCA.
- Konfigurowalna ścieżka narzędzi — bundlujemy, więc niepotrzebna.
- Panel snapshotów wbudowany w okno Explorera — używamy istniejącego `snapshot-gui`.
- Linia 2.x (GTK4) — osobna gałąź, poza tym zadaniem.

[`quzopl/ghostfs-kernel`]: https://github.com/quzopl/ghostfs-kernel
