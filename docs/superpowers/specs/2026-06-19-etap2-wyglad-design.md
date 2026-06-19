# Etap 2 — Wygląd: Explorer w stylu Windows 11

Data: 2026-06-19

## Cel

Sprawić, by odbrandowany Explorer (fork Thunar 4.20.8 z Etapu 1) wyglądał jak
ciemny Windows 11 Explorer i miał windowsowe domyślne ustawienia — niezależnie
od motywu GTK systemu (KDE Plasma).

## Decyzje (potwierdzone z użytkownikiem)

- Domyślny widok: **duże ikony z miniaturami** (`ThunarIconView`), miniatury
  „zawsze", bez limitu rozmiaru pliku — pod tysiące zdjęć.
- Siła motywu: **twarde wymuszenie** naszego CSS (priorytet aplikacji) + wariant
  ciemny wymuszony przez `GtkSettings`.
- Domyślny motyw: **ciemny** (jak Pythonowy Explorer: `Fluent · Ciemny`).

## Stan wyjściowy (co Thunar już ma)

| Ustawienie | Domyślne | Cel | Zmiana |
|---|---|---|---|
| `misc-folders-first` | `TRUE` | foldery najpierw | brak |
| `misc-single-click` | `FALSE` | podwójny klik | brak |
| `misc-thumbnail-max-file-size` | `0` (bez limitu) | bez limitu | brak |
| `default-view` | `"void"` | duże ikony | → `"ThunarIconView"` |
| `misc-thumbnail-mode` | `ONLY_LOCAL` | zawsze | → `THUNAR_THUMBNAIL_MODE_ALWAYS` |

## Wzorzec wyglądu (z `src/explorer/theme/dark.qss` Pythonowego Explorera)

Tło `#202020`, widoki `#1c1c1c`, tekst `#e6e6e6`, zaznaczenie `#2f3a4a`,
hover `#2c2c2c`, toolbar `#252525` z dolną krawędzią `#3a3a3a`, pasek statusu
`#252525`/`#9a9a9a`, menu `#2b2b2b` z krawędzią `#3a3a3a`, scrollbary uchwyt
`#3a3a3a` promień 6px (hover `#4a4a4a`), pole adresu/wyszukiwania `#1a1a1a`
z krawędzią `#3a3a3a` promień 5px. Font „Segoe UI", „Noto Sans", 13px.

## Komponenty

### A. Wbudowany ciemny motyw Win11
- Plik `branding/explorer.css` — port `dark.qss` na GTK3 CSS (selektory GTK:
  `window`, `treeview`, `.sidebar`, `headerbar`/`toolbar`, `menu`, `scrollbar`,
  `entry`, itd.).
- Instalacja do `install/share/explorer/explorer.css` (skrypt brandingu).
- Patch w `thunar_application_startup` (`thunar/thunar-application.c`): ustawia
  `gtk-application-prefer-dark-theme = TRUE` na domyślnym `GtkSettings` oraz
  ładuje `explorer.css` przez `GtkCssProvider` z
  `GTK_STYLE_PROVIDER_PRIORITY_APPLICATION` na domyślnym ekranie. Ścieżka CSS
  budowana z `DATADIR`/`PACKAGE_DATADIR` (stała kompilacji, prefiks lokalny).

### B. Domyślne ustawienia (patch w `thunar/thunar-preferences.c`)
- `default-view`: `"void"` → `"ThunarIconView"`.
- `misc-thumbnail-mode`: `THUNAR_THUMBNAIL_MODE_ONLY_LOCAL` →
  `THUNAR_THUMBNAIL_MODE_ALWAYS`.
- Domyślny zoom ikon: podnieść (większe miniatury) — właściwość
  `last-icon-view-zoom-level` / `THUNAR_ZOOM_LEVEL_*`.

### C. Miniatury
- `tumbler` działa, cache `~/.cache/thumbnails` istnieje. Tryb „zawsze" + brak
  limitu = tysiące zdjęć ładują miniatury. Bez zmian w kodzie.

## Architektura zmian

Wszystko jako patche odtwarzalne po `fetch-sources.sh`:
- `patches/04-theme-css.patch` — ładowanie CSS + dark w `thunar-application.c`.
- `patches/05-default-settings.patch` — domyślne wartości w `thunar-preferences.c`.
- `branding/explorer.css` — wersjonowany w repo (nie patch, własny plik).
- `scripts/install-branding.sh` — rozszerzony o instalację CSS.

## Definicja sukcesu

- `install/bin/explorer` startuje z ciemnym motywem Win11 niezależnie od motywu
  KDE (brak błędów krytycznych, CSS załadowany).
- Świeży kanał `explorer` / nowy profil pokazuje widok dużych ikon i miniatury.
- Domyślne właściwości mają nowe wartości (weryfikacja przez kod/odczyt).
- Systemowy Thunar i jego wygląd pozostają nietknięte.
