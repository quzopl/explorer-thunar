# Etap 3 — Funkcje: stałe pole wyszukiwania (jak Windows)

Data: 2026-06-19

## Cel

Dodać do Explorera **zawsze widoczne pole wyszukiwania** w prawej części paska
narzędzi (jak Windows Explorer), wykorzystujące natywny, rekurencyjny silnik
wyszukiwania Thunara.

## Decyzje (potwierdzone z użytkownikiem)

- **Miniatury wideo: pomijamy** — `ffmpegthumbnailer` nie instalujemy (brak zmian
  systemowych). Miniatury obrazów już działają.
- **Wyszukiwanie: stałe pole w pasku** (jak Windows), nie tylko `Ctrl+F`.

## Stan wyjściowy (co już jest)

- Wyszukiwanie pod `Ctrl+F` (`<Primary>f`), rekurencyjne, + przycisk-przełącznik
  lupy w pasku (`location_toolbar_item_search`).
- Mechanizm: `thunar_window_action_search` →
  `thunar_window_start_open_location (window, "Search: ")` — pasek lokalizacji
  wchodzi w tryb wyszukiwania, `thunar-path-entry` rozpoznaje prefiks „Search: ".
- `thunar_window_start_open_location (window, initial_text)` — uruchamia
  wyszukiwanie z dowolną frazą, gdy `initial_text` = „Search: " + zapytanie.
- `thunar_window_action_cancel_search (window)` — anuluje wyszukiwanie.

## Architektura zmiany (1 patch w C + CSS)

W `thunar_window_location_toolbar_create` (po utworzeniu przycisku lupy) dodać
zawsze widoczny `GtkSearchEntry` jako element paska:

- Callback `thunar_window_explorer_searchbox_activate (GtkSearchEntry*, ThunarWindow*)`:
  - pusty tekst → `thunar_window_action_cancel_search (window)`;
  - inaczej → `query = "Search: " + text`, `thunar_window_start_open_location (window, query)`.
- Sygnał `"activate"` (Enter) pola → callback (window jako `user_data`).
- Pole z placeholderem „Szukaj", szerokość ~220 px, `id` = „explorer-search"
  (żeby `load_items` traktował je jako znany element i nie ruszał pozycji).
- Reuse istniejącego silnika — żadnych zmian w backendzie wyszukiwania.

Stylizacja: `GtkSearchEntry` łapie się pod regułę `entry` w `explorer.css`
(ciemne `#1a1a1a`, ramka `#3a3a3a`, promień 5px) — bez dodatkowego CSS, ewentualnie
dopisać selektor `.searchbar`/`entry.search`.

## Definicja sukcesu

- W pasku narzędzi po prawej widoczne jest pole „Szukaj" niezależnie od trybu.
- Wpisanie frazy + Enter uruchamia rekurencyjne wyszukiwanie w bieżącym folderze
  (wyniki w widoku), pusty + Enter / Escape anuluje.
- Aplikacja startuje bez błędów krytycznych; systemowy Thunar nietknięty.
- Zmiana jako patch `patches/07-search-box.patch`.

## Poza zakresem

- Miniatury wideo (pominięte świadomie).
- Wyszukiwanie „as-you-type" w stałym polu (uruchamiamy na Enter — prościej,
  odporniej; wpisywanie filtruje już w natywnym trybie po starcie).
