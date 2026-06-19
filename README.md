# Explorer — menedżer plików w stylu Windows 11 na silniku Thunar

Fork **Thunar 4.20.8** odbrandowany jako osobna aplikacja **„Explorer"**,
z ciemnym motywem Windows 11, windowsowymi domyślnymi ustawieniami i stałym
polem wyszukiwania w pasku. Działa **obok** systemowego Thunara, nie nadpisując
go.

## Co zawiera

- **Wygląd:** wbudowany ciemny motyw Win11 (GTK CSS), wymuszony niezależnie od
  motywu systemu; tytuł okna „Explorer".
- **Domyślnie jak Windows:** duże ikony 150% z miniaturami, miniatury „zawsze"
  bez limitu rozmiaru (pod tysiące zdjęć — cache przez `tumbler`), foldery
  najpierw, podwójny klik.
- **Wyszukiwanie:** zawsze widoczne pole „Szukaj" w prawym górnym rogu paska
  (jak Windows) + natywne rekurencyjne wyszukiwanie Thunara (także `Ctrl+F`).
- **Izolacja:** osobny identyfikator aplikacji `eu.mizak.Explorer` i osobny kanał
  ustawień Xfconf `explorer`.

## Budowanie od zera

Wymagania: toolchain GTK3/XFCE (na Arch/Manjaro: `gtk3 libxfce4ui libxfce4util
exo xfconf gudev`), `gcc`, `make`, `patch`, `curl`, `tumbler` (miniatury).

```bash
bash scripts/fetch-sources.sh     # pobierz Thunar 4.20.8 do thunar-src/
bash scripts/apply-patches.sh     # nałóż patches/01..08
bash scripts/build.sh             # ./configure + make + make install -> install/
bash scripts/install-branding.sh  # binarka explorer, .desktop, ikona, CSS
```

Uruchomienie: `./install/bin/explorer`

## Weryfikacja

```bash
bash scripts/verify-etap1.sh   # fundament: osobny app-id, obok systemowego Thunara
bash scripts/verify-etap2.sh   # wygląd: CSS, start bez błędów
bash scripts/verify-etap3.sh   # pole wyszukiwania w pasku
```

## Struktura

- `thunar-src/` — źródła Thunara (ignorowane przez git; odtwarzalne z tarballa).
- `patches/` — wszystkie zmiany w C (odtwarzalne po `fetch-sources.sh`).
- `branding/` — `explorer.desktop`, `explorer.css` (motyw Win11).
- `scripts/` — pobieranie, patche, build, branding, weryfikacja.
- `docs/superpowers/` — specyfikacje i plany etapów.

Miniatury wideo (opcjonalnie): `sudo pacman -S ffmpegthumbnailer` — `tumbler`
wykryje je automatycznie.
