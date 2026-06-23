# Etap 2 — Wygląd (plan implementacji)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans / subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Explorer wygląda jak ciemny Windows 11 Explorer i ma windowsowe domyślne ustawienia, niezależnie od motywu KDE.

**Architecture:** Plik `branding/explorer.css` (port `dark.qss`) instalowany do `install/share/explorer/`, ładowany przez patch w `thunar_application_startup` z priorytetem aplikacji + wymuszony wariant ciemny. Domyślne ustawienia zmienione patchem w `thunar-preferences.c`. Zmiany jako patche `04`/`05`.

**Tech Stack:** C, GTK3 CSS, GtkCssProvider, GtkSettings, autotools.

## Global Constraints

- Bazuje na Etapie 1 (źródła w `thunar-src/`, build przez `scripts/build.sh`, prefiks `install/`).
- Zmiany w C utrwalane jako patche w `patches/`; pliki własne (`branding/explorer.css`) wersjonowane wprost.
- Twarde wymuszenie CSS: `GTK_STYLE_PROVIDER_PRIORITY_APPLICATION` + `gtk-application-prefer-dark-theme = TRUE`.
- Nie dotykać systemowego Thunara ani jego kanału `thunar`.
- Po każdej zmianie w C: `bash scripts/build.sh` + `bash scripts/install-branding.sh`.

---

### Task 1: Plik motywu `branding/explorer.css`

**Files:**
- Create: `branding/explorer.css`

- [ ] **Step 1: Napisz CSS (port dark.qss na GTK3)**

Create `branding/explorer.css` z regułami: tło okna `#202020`/tekst `#e6e6e6`, widoki `#1c1c1c`, zaznaczenie `#2f3a4a`, hover `#2c2c2c`, toolbar/headerbar `#252525`, menu `#2b2b2b`, scrollbar uchwyt `#3a3a3a` r=6, entry `#1a1a1a` r=5, sidebar `#1c1c1c`. (Pełna treść w Step 1 implementacji.)

- [ ] **Step 2: Walidacja składni CSS**

Run: `gtk-builder-tool 2>/dev/null; python3 -c "print(open('branding/explorer.css').read()[:50])"`
Expected: plik czytelny; (GTK zwaliduje przy ładowaniu w Task 3).

- [ ] **Step 3: Commit**

```bash
git add branding/explorer.css
git commit -m "feat: ciemny motyw Win11 jako GTK CSS (port dark.qss)"
```

---

### Task 2: Instalacja CSS przez skrypt brandingu

**Files:**
- Modify: `scripts/install-branding.sh`

**Interfaces:**
- Produces: `install/share/explorer/explorer.css`.

- [ ] **Step 1: Dodaj instalację CSS do skryptu**

W `scripts/install-branding.sh` dodaj przed echo końcowym:
```bash
mkdir -p "$PREFIX/share/explorer"
install -m644 branding/explorer.css "$PREFIX/share/explorer/explorer.css"
```

- [ ] **Step 2: Uruchom i zweryfikuj**

Run: `bash scripts/install-branding.sh && ls -la install/share/explorer/explorer.css`
Expected: plik istnieje.

- [ ] **Step 3: Commit**

```bash
git add scripts/install-branding.sh
git commit -m "build: instaluj explorer.css do share/explorer/"
```

---

### Task 3: Załaduj CSS + wymuś ciemny (patch w thunar-application.c)

**Files:**
- Modify: `thunar-src/thunar/thunar-application.c` (funkcja `thunar_application_startup`)
- Create: `patches/04-theme-css.patch`

- [ ] **Step 1: Backup pliku**

Run: `cp thunar-src/thunar/thunar-application.c thunar-src/thunar/thunar-application.c.t2`

- [ ] **Step 2: Dodaj ładowanie CSS w `thunar_application_startup`**

Na początku ciała `thunar_application_startup` (po `THUNAR_APPLICATION (gapp)`) dodaj:
```c
  /* Explorer: wymuś ciemny motyw Win11 niezależnie od motywu systemu */
  {
    GtkSettings *settings = gtk_settings_get_default ();
    if (settings != NULL)
      g_object_set (settings, "gtk-application-prefer-dark-theme", TRUE, NULL);

    GtkCssProvider *provider = gtk_css_provider_new ();
    gchar *css_path = g_build_filename (DATADIR, "explorer", "explorer.css", NULL);
    if (gtk_css_provider_load_from_path (provider, css_path, NULL))
      gtk_style_context_add_provider_for_screen (gdk_screen_get_default (),
                                                 GTK_STYLE_PROVIDER (provider),
                                                 GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_free (css_path);
    g_object_unref (provider);
  }
```
Jeśli `DATADIR` nie jest zdefiniowany w tym pliku, sprawdź `config.h` (`grep -n "define DATADIR\|PACKAGE_DATADIR" config.h`) i użyj właściwej stałej. Upewnij się, że nagłówki `gtk/gtk.h` są włączone (są w Thunarze).

- [ ] **Step 3: Przebuduj i zainstaluj**

Run: `bash scripts/build.sh && bash scripts/install-branding.sh`
Expected: `OK: zainstalowano` + `OK: branding zainstalowany`, bez błędów kompilacji.

- [ ] **Step 4: Test — start z CSS, bez błędów krytycznych**

Run:
```bash
timeout 7 ./install/bin/explorer /tmp 2>/tmp/exp-theme.err & MYPID=$!
for _ in 1 2 3 4 5; do busctl --user list 2>/dev/null | grep -q io.github.quzopl.Explorer && break; sleep 1; done
grep -i "Theme parsing error\|segfault\|critical" /tmp/exp-theme.err && echo "SĄ BŁĘDY CSS" || echo "CSS OK (bez błędów parsowania)"
wait $MYPID 2>/dev/null
```
Expected: `CSS OK (bez błędów parsowania)`. (Jeśli są błędy parsowania CSS — popraw `explorer.css` i wróć do Task 1.)

- [ ] **Step 5: Wygeneruj patch i commit**

```bash
diff -u thunar-src/thunar/thunar-application.c.t2 thunar-src/thunar/thunar-application.c | sed 's|thunar-src/||g' > patches/04-theme-css.patch
git add patches/04-theme-css.patch
git commit -m "feat: patch — ładuj wbudowany CSS Win11 i wymuś ciemny wariant"
```

---

### Task 4: Domyślne ustawienia (patch w thunar-preferences.c)

**Files:**
- Modify: `thunar-src/thunar/thunar-preferences.c`
- Create: `patches/05-default-settings.patch`

- [ ] **Step 1: Backup**

Run: `cp thunar-src/thunar/thunar-preferences.c thunar-src/thunar/thunar-preferences.c.t2`

- [ ] **Step 2: Zmień `default-view` na ThunarIconView**

W `g_param_spec_string ("default-view", ...)` zmień wartość domyślną `"void"` na `"ThunarIconView"`.

- [ ] **Step 3: Zmień `misc-thumbnail-mode` na ALWAYS**

W `g_param_spec_enum ("misc-thumbnail-mode", ...)` zmień domyślną `THUNAR_THUMBNAIL_MODE_ONLY_LOCAL` na `THUNAR_THUMBNAIL_MODE_ALWAYS`.

- [ ] **Step 4: Podnieś domyślny zoom ikon (większe miniatury)**

Zlokalizuj `last-icon-view-zoom-level` (`grep -n "last-icon-view-zoom-level" thunar/thunar-preferences.c`); ustaw domyślną wartość na większy poziom (np. `THUNAR_ZOOM_LEVEL_150_PERCENT` lub odpowiednik „dużych ikon"; sprawdź enum w `thunar/thunar-enum-types.h`).

- [ ] **Step 5: Przebuduj**

Run: `bash scripts/build.sh && bash scripts/install-branding.sh`
Expected: kompiluje się bez błędów.

- [ ] **Step 6: Test — świeży kanał ma nowe domyślne**

Run:
```bash
# wyczyść nasz kanał, by wymusić domyślne
xfconf-query -c explorer -p /default-view -r 2>/dev/null || true
xfconf-query -c explorer -p /misc-thumbnail-mode -r 2>/dev/null || true
timeout 6 ./install/bin/explorer /tmp >/dev/null 2>&1 & MYPID=$!
for _ in 1 2 3 4 5; do busctl --user list 2>/dev/null | grep -q io.github.quzopl.Explorer && break; sleep 1; done
sleep 1
echo "thumbnail-mode: $(xfconf-query -c explorer -p /misc-thumbnail-mode 2>/dev/null || echo '(domyślne z param-spec)')"
wait $MYPID 2>/dev/null
```
Expected: aplikacja używa widoku ikon i trybu miniatur „always" (wartość z param-spec, gdy kanał pusty). Brak błędów.

- [ ] **Step 7: Patch i commit**

```bash
diff -u thunar-src/thunar/thunar-preferences.c.t2 thunar-src/thunar/thunar-preferences.c | sed 's|thunar-src/||g' > patches/05-default-settings.patch
git add patches/05-default-settings.patch
git commit -m "feat: patch — domyślnie duże ikony, miniatury zawsze"
```

---

### Task 5: Weryfikacja Etapu 2 + miniatury wideo opcjonalnie

**Files:**
- Modify: `scripts/verify-etap1.sh` → dorzuć sekcję Etapu 2 (albo nowy `scripts/verify-etap2.sh`)

- [ ] **Step 1: Skrypt weryfikacyjny Etapu 2**

Create `scripts/verify-etap2.sh`:
```bash
#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
echo "== CSS zainstalowany =="
[ -f install/share/explorer/explorer.css ] && echo "css OK" || { echo "BRAK css"; fail=1; }
echo "== start bez błędów parsowania CSS =="
timeout 7 ./install/bin/explorer /tmp 2>/tmp/exp-v2.err & MYPID=$!
for _ in 1 2 3 4 5; do busctl --user list 2>/dev/null | grep -q io.github.quzopl.Explorer && break; sleep 1; done
if grep -qi "Theme parsing error\|segfault\|CRITICAL" /tmp/exp-v2.err; then echo "BŁĘDY"; cat /tmp/exp-v2.err; fail=1; else echo "start OK"; fi
wait $MYPID 2>/dev/null
[ "$fail" = 0 ] && echo "ETAP 2: SUKCES" || echo "ETAP 2: SĄ BŁĘDY"
exit $fail
```

- [ ] **Step 2: Uruchom**

Run: `bash scripts/verify-etap2.sh`
Expected: `ETAP 2: SUKCES`, kod 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/verify-etap2.sh
git commit -m "test: skrypt weryfikacyjny Etapu 2"
```

---

## Self-Review

- Motyw CSS → Task 1-3 ✓; domyślne ustawienia → Task 4 ✓; miniatury (tryb always) → Task 4 ✓; weryfikacja → Task 5 ✓.
- Stałe nazwane spójnie: `io.github.quzopl.Explorer`, kanał `explorer`, `explorer.css`, `install/share/explorer/`.
- Discovery (`DATADIR` w config.h, enum zoom/thumbnail) ma konkretne komendy `grep` — nie placeholdery.
