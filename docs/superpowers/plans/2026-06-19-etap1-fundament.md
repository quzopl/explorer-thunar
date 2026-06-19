# Etap 1 — Fundament: Explorer na silniku Thunar (plan implementacji)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pobrać źródła Thunar 4.20.8, zbudować je przez meson do lokalnego prefiksu i odbrandować jako osobną aplikację „Explorer", która uruchamia się obok niezakłóconego systemowego Thunara.

**Architecture:** Fork źródeł Thunar 4.20.8 w katalogu `thunar-src/`. Build meson → ninja do prefiksu `install/` (bez dotykania `/usr`). Odbrandowanie przez zmianę identyfikatora aplikacji/D-Bus, kanału Xfconf, nazwy binarki i pliku `.desktop` — tak by nasza instancja była niezależna od systemowej.

**Tech Stack:** C, GTK3 (3.24.52), meson/ninja, libxfce4ui, libxfce4util, exo, glib2, Xfconf, D-Bus.

## Global Constraints

- Wszystko żyje w `/mnt/swiezak/explorer-thunar` (osobne repo git, poza repo Pythonowego Explorera).
- Wersja Thunara: **dokładnie 4.20.8** (zgodna z systemową).
- Instalacja **tylko** do `install/` w repo — nigdy do `/usr` (`ninja install` z prefiksem lokalnym, bez `sudo`).
- Nowy identyfikator aplikacji/D-Bus: **`eu.mizak.Explorer`** (zastępuje `org.xfce.Thunar`).
- Nowy kanał Xfconf: **`explorer`** (zastępuje `thunar`) — izolacja ustawień.
- Nazwa binarki: **`explorer`**. Nazwa widoczna: **„Explorer"**.
- Systemowy Thunar (`/usr/bin/thunar`) i jego konfiguracja muszą pozostać nietknięte; obie aplikacje muszą dać się uruchomić równolegle.
- Artefakty buildu (`build/`, `install/`, `thunar-src/`) są w `.gitignore` — nie commitujemy ich.
- Każde polecenie uruchamiające GUI w teście robimy w trybie offscreen: `QT_QPA_PLATFORM=offscreen` nie dotyczy GTK; dla GTK używamy `GDK_BACKEND=x11`/`wayland` z bieżącej sesji, a smoke-test robimy z `timeout` (kod 124 = wciąż działa = OK).

---

### Task 1: Pobranie i rozpakowanie źródeł Thunar 4.20.8

**Files:**
- Create: `thunar-src/` (rozpakowane źródła, ignorowane przez git)
- Create: `scripts/fetch-sources.sh`

**Interfaces:**
- Produces: katalog `thunar-src/meson.build` (korzeń źródeł Thunara) używany przez kolejne zadania.

- [ ] **Step 1: Napisz skrypt pobierający źródła**

Create `scripts/fetch-sources.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
VER=4.20.8
SERIES=4.20
TARBALL="thunar-${VER}.tar.bz2"
URL="https://archive.xfce.org/src/xfce/thunar/${SERIES}/${TARBALL}"
mkdir -p .cache
if [ ! -f ".cache/${TARBALL}" ]; then
  echo "Pobieram ${URL}"
  curl -fL --retry 3 -o ".cache/${TARBALL}" "${URL}"
fi
rm -rf thunar-src
mkdir -p thunar-src
tar -xjf ".cache/${TARBALL}" -C thunar-src --strip-components=1
echo "OK: rozpakowano do thunar-src/"
```

- [ ] **Step 2: Uruchom skrypt**

Run: `bash scripts/fetch-sources.sh`
Expected: `OK: rozpakowano do thunar-src/` (jeśli `.tar.bz2` nie istnieje, spróbuj `.tar.xz` — zmień `TARBALL`/`tar -xJf`).

- [ ] **Step 3: Zweryfikuj wersję i system buildu**

Run: `grep -m1 "version" thunar-src/meson.build | head -1; ls thunar-src/meson.build`
Expected: wersja `4.20.8` w `meson.build`, plik `meson.build` istnieje (Thunar 4.20 buduje się meson-em).

- [ ] **Step 4: Commit (tylko skrypt, nie źródła)**

```bash
git add scripts/fetch-sources.sh
git commit -m "build: skrypt pobierający źródła Thunar 4.20.8"
```

---

### Task 2: Build bazowy do lokalnego prefiksu + smoke test

**Files:**
- Create: `scripts/build.sh`
- Use: `thunar-src/` (z Task 1)

**Interfaces:**
- Consumes: `thunar-src/meson.build`.
- Produces: `install/bin/thunar` (binar bazowy, jeszcze nieodbrandowany) — używany jako baza w Task 3.

- [ ] **Step 1: Napisz skrypt budujący**

Create `scripts/build.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX="$PWD/install"
meson setup build thunar-src --prefix="$PREFIX" --reconfigure 2>/dev/null \
  || meson setup build thunar-src --prefix="$PREFIX"
ninja -C build
ninja -C build install
echo "OK: zainstalowano do $PREFIX"
```

- [ ] **Step 2: Uruchom build — rozwiąż brakujące zależności**

Run: `bash scripts/build.sh`
Expected: jeśli `meson setup` zgłosi brak zależności (np. `exo-2`, `libxfce4ui-2`, `gtk+-3.0`, `libxfce4util-1.0`, `Xfconf`), doinstaluj pakiety deweloperskie przez `pacman -S --needed <pakiet>` i powtórz. Sukces: `OK: zainstalowano do .../install`.

- [ ] **Step 3: Smoke test — binar startuje**

Run: `timeout 5 ./install/bin/thunar --version; echo "exit=$?"`
Expected: wypisuje `Thunar 4.20.8` (lub baner wersji), `exit=0`.

- [ ] **Step 4: Smoke test — okno startuje (bez crasha)**

Run: `timeout 6 ./install/bin/thunar /tmp; echo "exit=$?"`
Expected: `exit=124` (proces żył do timeoutu = uruchomił się poprawnie) i brak komunikatu o segfault/aborcie. Uwaga: bez `--daemon` instancja może dołączyć do systemowego demona — to rozwiązujemy w Task 3.

- [ ] **Step 5: Commit**

```bash
git add scripts/build.sh
git commit -m "build: skrypt meson buildujący Thunara do lokalnego install/"
```

---

### Task 3: Osobny identyfikator aplikacji/D-Bus (`eu.mizak.Explorer`)

To najważniejsze zadanie Etapu 1: bez zmiany app-id nasz binar pod single-instance „dogada się" z działającym systemowym demonem Thunara zamiast być osobną aplikacją.

**Files:**
- Modify: pliki źródłowe w `thunar-src/` zawierające stałą `org.xfce.Thunar` (zidentyfikowane w Step 1)
- Use: `scripts/build.sh`

**Interfaces:**
- Consumes: drzewo `thunar-src/` zbudowane w Task 2.
- Produces: `install/bin/thunar` z identyfikatorem aplikacji `eu.mizak.Explorer`.

- [ ] **Step 1: Zlokalizuj identyfikator aplikacji i nazwy D-Bus**

Run: `grep -rn "org\.xfce\.Thunar\|org\.xfce\.FileManager\|application_id\|G_APPLICATION" thunar-src/thunar/thunar-application.c thunar-src/thunar/*.c | head -40`
Expected: znajdź miejsce, gdzie tworzony jest `GApplication`/`GtkApplication` z `application-id` oraz definicje nazw D-Bus (np. w `thunar-application.c`, ewentualnie `thunar-dbus-service.c`). Zanotuj dokładne stałe.

- [ ] **Step 2: Test PRZED zmianą — pokaż obecny app-id**

Run: `grep -rn "org.xfce.Thunar" thunar-src/thunar/thunar-application.c`
Expected: znajduje wystąpienie(a) z `org.xfce.Thunar` jako application-id. (To „test, który ma wykazać stan początkowy".)

- [ ] **Step 3: Zmień application-id na `eu.mizak.Explorer`**

W pliku/plikach z application-id (najpewniej `thunar-src/thunar/thunar-application.c`) zmień ciąg `"org.xfce.Thunar"` użyty jako **application-id** na `"eu.mizak.Explorer"`. NIE zmieniaj na tym etapie wewnętrznych ścieżek obiektów D-Bus współdzielonej usługi menedżera plików (`org.xfce.FileManager`), jeśli służą integracji — zmieniamy wyłącznie unikatową nazwę instancji (application-id), aby uzyskać osobny single-instance.

- [ ] **Step 4: Przebuduj**

Run: `bash scripts/build.sh`
Expected: `OK: zainstalowano do .../install`.

- [ ] **Step 5: Test — osobna instancja obok systemowego Thunara**

Run:
```bash
# upewnij się, że systemowy demon działa lub uruchom go
timeout 8 /usr/bin/thunar --daemon &
sleep 1
timeout 6 ./install/bin/thunar /tmp & MYPID=$!
sleep 2
# nasza instancja ma własną nazwę na magistrali:
busctl --user list | grep -i "eu.mizak.Explorer" && echo "OSOBNA INSTANCJA OK"
wait $MYPID 2>/dev/null; echo "done"
```
Expected: linia z `eu.mizak.Explorer` na magistrali sesyjnej → `OSOBNA INSTANCJA OK`. Systemowy `thunar` nie został zamknięty ani przejął okna.

- [ ] **Step 6: Commit**

```bash
git add thunar-src
git commit -m "feat: osobny application-id eu.mizak.Explorer (instancja niezależna od systemowego Thunara)"
```

Uwaga: `thunar-src/` jest w `.gitignore`, więc commit źródeł wymaga `git add -f thunar-src` LUB usunięcia `thunar-src/` z `.gitignore` na rzecz patcha. **Decyzja:** zamiast commitować całe drzewo, zapiszemy zmianę jako **patch** — patrz Step 7.

- [ ] **Step 7: Zapisz zmianę jako patch (zamiast commitować całe źródła)**

```bash
mkdir -p patches
( cd thunar-src && git init -q 2>/dev/null; true )   # jeśli brak repo w źródłach, użyj diff względem tarballa
# Wygeneruj patch ręcznie z backupu pliku przed zmianą, np.:
#   cp thunar/thunar-application.c thunar/thunar-application.c.orig  (przed Step 3)
#   diff -u thunar/thunar-application.c.orig thunar/thunar-application.c > ../patches/01-app-id.patch
git -C .. add patches/01-app-id.patch
```

Run: `git add patches/01-app-id.patch && git commit -m "feat: patch — osobny application-id eu.mizak.Explorer"`
Expected: patch zacommitowany; `thunar-src/` pozostaje ignorowane. (Patch będzie odtwarzalny po `fetch-sources.sh`.)

---

### Task 4: Osobny kanał Xfconf (`explorer`) — izolacja ustawień

Bez tego ustawienia naszej apki (motyw/sort w Etapie 2) pisałyby do kanału `thunar` i wyciekały do systemowego Thunara.

**Files:**
- Modify: pliki w `thunar-src/` używające kanału Xfconf `"thunar"`
- Create: `patches/02-xfconf-channel.patch`

**Interfaces:**
- Consumes: `thunar-src/` po Task 3.
- Produces: binar zapisujący/odczytujący ustawienia z kanału Xfconf `explorer`.

- [ ] **Step 1: Zlokalizuj nazwę kanału Xfconf**

Run: `grep -rn "xfconf_channel_get\|\"thunar\"" thunar-src/thunar/thunar-preferences.c | head`
Expected: znajdź wywołanie `xfconf_channel_get("thunar")` (lub `_get_default`/nazwę kanału) w `thunar-preferences.c`.

- [ ] **Step 2: Zrób kopię pliku przed zmianą**

Run: `cp thunar-src/thunar/thunar-preferences.c thunar-src/thunar/thunar-preferences.c.orig`
Expected: kopia utworzona (do wygenerowania patcha).

- [ ] **Step 3: Zmień nazwę kanału na `explorer`**

W `thunar-src/thunar/thunar-preferences.c` zmień nazwę kanału Xfconf z `"thunar"` na `"explorer"` w wywołaniu pobierającym kanał.

- [ ] **Step 4: Przebuduj**

Run: `bash scripts/build.sh`
Expected: `OK: zainstalowano do .../install`.

- [ ] **Step 5: Test — ustawienia idą do kanału `explorer`, nie `thunar`**

Run:
```bash
xfconf-query -c explorer -lv 2>/dev/null | head || true
timeout 5 ./install/bin/thunar /tmp >/dev/null 2>&1 &
sleep 2
xfconf-query -c explorer -l && echo "KANAL EXPLORER OK"
```
Expected: kanał `explorer` istnieje / da się odpytać → `KANAL EXPLORER OK`. Kanał `thunar` systemowego Thunara pozostaje osobny.

- [ ] **Step 6: Wygeneruj patch i commit**

```bash
diff -u thunar-src/thunar/thunar-preferences.c.orig thunar-src/thunar/thunar-preferences.c > patches/02-xfconf-channel.patch || true
git add patches/02-xfconf-channel.patch
git commit -m "feat: patch — osobny kanał Xfconf 'explorer' (izolacja ustawień)"
```

---

### Task 5: Branding — binarka `explorer`, `.desktop`, ikona, nazwa widoczna

**Files:**
- Create: `scripts/install-branding.sh`
- Create: `branding/explorer.desktop`
- Modify: pliki w `thunar-src/` z widoczną nazwą programu (About/nazwa aplikacji), jeśli trzeba — patch `patches/03-name.patch`

**Interfaces:**
- Consumes: `install/bin/thunar` po Task 4.
- Produces: `install/bin/explorer` (binar/dowiązanie), `install/share/applications/explorer.desktop`.

- [ ] **Step 1: Plik .desktop dla naszej apki**

Create `branding/explorer.desktop`:

```ini
[Desktop Entry]
Type=Application
Version=1.0
Name=Explorer
Comment=Menedżer plików w stylu Windows na silniku Thunar
Exec=explorer %F
Icon=system-file-manager
Terminal=false
Categories=System;Utility;Core;GTK;FileManager;
StartupNotify=true
MimeType=inode/directory;
```

- [ ] **Step 2: Skrypt instalujący branding**

Create `scripts/install-branding.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX="$PWD/install"
# binarka explorer = dowiązanie do zbudowanego thunar
ln -sf thunar "$PREFIX/bin/explorer"
# plik .desktop
mkdir -p "$PREFIX/share/applications"
install -m644 branding/explorer.desktop "$PREFIX/share/applications/explorer.desktop"
echo "OK: branding zainstalowany"
```

- [ ] **Step 3: Uruchom**

Run: `bash scripts/install-branding.sh`
Expected: `OK: branding zainstalowany`; istnieje `install/bin/explorer` i `install/share/applications/explorer.desktop`.

- [ ] **Step 4: Test — uruchomienie pod nazwą `explorer`**

Run: `timeout 5 ./install/bin/explorer --version; echo "exit=$?"`
Expected: baner wersji, `exit=0`.

- [ ] **Step 5: (Opcjonalnie) Nazwa widoczna „Explorer"**

Run: `grep -rn "PACKAGE_NAME\|\"Thunar\"\|g_set_application_name" thunar-src/thunar/thunar-application.c | head`
Expected: jeśli jest `g_set_application_name("Thunar")`, zrób kopię `.orig`, zmień na `"Explorer"`, przebuduj (`bash scripts/build.sh && bash scripts/install-branding.sh`), wygeneruj `patches/03-name.patch`. Jeśli nie ma — pomiń.

- [ ] **Step 6: Commit**

```bash
git add scripts/install-branding.sh branding/explorer.desktop patches/03-name.patch 2>/dev/null || git add scripts/install-branding.sh branding/explorer.desktop
git commit -m "feat: branding — binarka explorer, .desktop i nazwa Explorer"
```

---

### Task 6: Weryfikacja końcowa Etapu 1 — działanie obok systemowego Thunara

**Files:**
- Create: `scripts/verify-etap1.sh`

**Interfaces:**
- Consumes: pełny `install/` po Tasks 1-5.
- Produces: skrypt potwierdzający definicję sukcesu Etapu 1.

- [ ] **Step 1: Skrypt weryfikacyjny**

Create `scripts/verify-etap1.sh`:

```bash
#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
echo "== 1. binar explorer istnieje i ma wersję =="
timeout 5 ./install/bin/explorer --version || fail=1
echo "== 2. systemowy thunar nietknięty =="
/usr/bin/thunar --version || fail=1
echo "== 3. osobny app-id na magistrali =="
timeout 6 ./install/bin/explorer /tmp >/dev/null 2>&1 &
sleep 2
busctl --user list 2>/dev/null | grep -q "eu.mizak.Explorer" && echo "app-id OK" || { echo "BRAK app-id"; fail=1; }
echo "== 4. osobny kanał xfconf =="
xfconf-query -c explorer -l >/dev/null 2>&1 && echo "kanal OK" || echo "(kanal jeszcze pusty — OK jeśli brak zapisów)"
[ "$fail" = 0 ] && echo "ETAP 1: SUKCES" || echo "ETAP 1: SĄ BŁĘDY"
exit $fail
```

- [ ] **Step 2: Uruchom weryfikację**

Run: `bash scripts/verify-etap1.sh`
Expected: `ETAP 1: SUKCES`, kod wyjścia 0; systemowy thunar wypisuje swoją wersję (nietknięty), nasz `explorer` ma osobny app-id `eu.mizak.Explorer`.

- [ ] **Step 3: Commit**

```bash
git add scripts/verify-etap1.sh
git commit -m "test: skrypt weryfikacyjny definicji sukcesu Etapu 1"
```

---

## Self-Review (wykonane przy pisaniu planu)

**Pokrycie speca:**
- Pobranie źródeł 4.20.8 → Task 1 ✓
- Build meson do lokalnego prefiksu + smoke test → Task 2 ✓
- Odbrandowanie: app-id/D-Bus → Task 3 ✓; nazwa binarki/.desktop/ikona/nazwa widoczna → Task 5 ✓
- Izolacja konfiguracji (kanał Xfconf) → Task 4 ✓ (rozszerza notatkę „config isolation" ze speca)
- Weryfikacja działania obok systemowego → Task 6 ✓

**Placeholdery:** kroki, które zależą od struktury źródeł (dokładny plik z app-id, nazwa kanału), zawierają konkretne komendy `grep` do zlokalizowania miejsca przed zmianą — to świadoma „discovery", nie placeholder. Patche generowane z kopii `.orig`.

**Spójność typów/nazw:** `eu.mizak.Explorer` i kanał `explorer` użyte spójnie w Task 3, 4 i 6. Binarka `explorer` spójnie w Task 5 i 6.

**Uwaga o commitowaniu źródeł:** `thunar-src/` jest ignorowane; zmiany w C utrwalamy jako patche w `patches/` (odtwarzalne po `fetch-sources.sh`), nie jako commit całego drzewa.
