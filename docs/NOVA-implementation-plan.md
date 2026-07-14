# NOVA — pełny plan wdrożenia wyglądu

## 1. Uczciwa diagnoza: dlaczego dotychczasowe podejście nie sięga NOVA

Dotąd „Explorer" = **Thunar 4.20 + motyw CSS + drobne patche C**. To świetnie działa dla
kolorów, promieni, pigułek na pasku i menu. Ale mockup NOVA to nie skórka — to inny
**układ i inne widżety**, a te w Thunarze są nie do przestylowania:

| Element NOVA | Widżet w Thunarze | Czy da się CSS-em? |
|---|---|---|
| Kafelki-karty (ikona na kolorowym tle, zaokrąglone) | `GtkIconView` (komórki rysowane przez cell-renderery) | ❌ nie — brak kart per-komórka |
| Pigułkowe wiersze sidebara, karty urządzeń, MAPA DYSKU | `GtkTreeView` (jedna kolumna, cell-renderery) | ❌ nie — brak layoutu per-wiersz |
| Gradientowe ikony folderów | motyw ikon (osobny) | ⚠️ tylko przez nowy theme ikon |
| Panel podglądu z metadanymi + „Wgląd AI" | brak w Thunarze | ❌ trzeba napisać |
| AUTO-KOLEKCJE / Indeks AI / paleta Ctrl+K z akcjami | brak (to funkcje, nie styl) | ❌ trzeba napisać silnik |

Kluczowy fakt architektoniczny: `thunarx` (system wtyczek) udostępnia tylko
**menu-provider / property-page-provider / renamer-provider / preferences-provider**.
Nie ma „view-provider" ani „sidebar-provider" — czyli **wtyczką nie podmienimy ani siatki
plików, ani panelu bocznego**. Widoki są `GtkScrolledWindow`/`GtkIconView` wewnątrz kodu
Thunara; dałoby się je osadzić w innym oknie, ale nie zastąpić.

Wniosek: przy założeniu „to ma być Thunar" wygląd jest **z definicji ograniczony**. Żeby
wyglądać jak NOVA, trzeba świadomie wybrać, ile Thunara zostawiamy.

## 2. Trzy drogi (do wyboru — to jest decyzja produktowa)

### Droga A — „NOVA-flavored" (dalsze patche na Thunarze)
Zostajemy przy Thunarze, dociskamy motyw i drobne patche C (to, co robiliśmy).
- **Efekt:** kolory, pigułki, poświata, pasek zaznaczenia, paski dysków, Ctrl+K, karty paneli.
  Realnie ~50–60% „ducha" NOVA. Kafelki, pigułkowy sidebar, mapa dysku, panel podglądu —
  **nieosiągalne**.
- **Koszt:** mały (dni). Zero ryzyka regresji funkcji Thunara.
- **Dla kogo:** jeśli priorytetem jest stabilny menedżer plików, a NOVA ma być „inspiracją".

### Droga B — Custom GTK shell wokół widoku Thunara (rekomendowana)
Piszemy **własne okno GTK3** (nasz kod, nie patch), które:
- ma **własny sidebar** (GtkListBox z prawdziwymi wierszami-pigułkami: MIEJSCA,
  AUTO-KOLEKCJE, URZĄDZENIA z kartami zajętości, MAPA DYSKU jako pasek),
- ma **własny header** (logo, breadcrumbs-pigułki, pole „Szukaj / Ctrl K", przełącznik widoku, kropki okna),
- ma **własny pasek zaznaczenia** i **panel podglądu** (metadane pliku po prawej),
- w **środku osadza widok plików Thunara** (`ThunarStandardView` to `GtkScrolledWindow` — można
  go umieścić jako child) LUB własny `GtkFlowBox` z kafelkami-kartami renderowanymi z `GFileInfo`.
- operacje plikowe (kopiuj/przenieś/kosz/właściwości) wołamy przez `gio` albo przez wywołanie
  `thunar` w tle.
- **Efekt:** ~80–90% wyglądu NOVA. Prawdziwe karty, pigułkowy sidebar, mapa dysku, panel podglądu.
  Kafelki jako karty = tak, jeśli zrobimy własny `GtkFlowBox` (rekomendowane) zamiast osadzać `GtkIconView`.
- **Koszt:** średnio-duży (1–3 tygodnie). Ryzyko: część zaawansowanych funkcji Thunara (bulk rename,
  UCA, split-view) trzeba by podpiąć na nowo albo odpalać przez menu Thunara.
- **Dla kogo:** jeśli NOVA ma być realnie rozpoznawalna, a nie „w stylu".

### Droga C — Nowa aplikacja (pixel-match NOVA)
Piszemy menedżer od zera: **GTK4 + libadwaita** (natywnie) albo **Tauri/Electron** (mockup to HTML,
więc kod z projektu można wprost wykorzystać). Operacje na plikach przez `gio`/Rust.
- **Efekt:** 1:1 z mockupem, łącznie z animacjami, gradientami, paletą poleceń.
- **Koszt:** duży (tygodnie). To już **nie jest fork Thunara** — porzucamy silnik.
- **Dla kogo:** jeśli NOVA jest celem nadrzędnym, a „na Thunarze" było tylko środkiem.

## 3. Plan dla drogi B (rekomendacja) — fazy

**Faza 0 — szkielet (0.5 dnia).** Nowy plik `explorer-shell/` (GtkApplication, okno CSD z gridem:
header / sidebar / content / preview). Motyw NOVA jako jedyny CSS. Bez logiki — sam layout kart.

**Faza 1 — sidebar (2–3 dni).** `GtkListBox`: nagłówki sekcji, wiersze MIEJSCA (Dom/Dokumenty/…),
karty URZĄDZENIA (nazwa + `GtkLevelBar` + „X GB z Y"), pasek MAPA DYSKU. Dane z `GVolumeMonitor` +
`g_file_query_filesystem_info`. Klik = zmiana katalogu.

**Faza 2 — widok plików jako karty (3–4 dni).** `GtkFlowBox` z kafelkami: ikona z `GFileInfo`
na zaokrąglonym tle wg typu, nazwa, rozmiar. Zaznaczanie (multi), dwuklik = otwórz przez
`g_app_info_launch_default_for_uri`. Widok listy jako `GtkColumnView`/`GtkTreeView` z NAZWA/ROZMIAR/TYP/ZMIENIONO/TAG.

**Faza 3 — header + nawigacja (2 dni).** Breadcrumbs-pigułki (klik = skok), historia wstecz/dalej,
pole „Szukaj / Ctrl K" (filtr na `GFileInfo`), przełącznik widoku, kropki okna.

**Faza 4 — operacje plikowe (2–3 dni).** Kopiuj/wytnij/wklej (`gio`), Kosz (`g_file_trash`),
zmiana nazwy, właściwości, „Otwórz w terminalu", etykiety kolorów (nasze metadane gvfs — reużywamy
kod z Explorera). Pasek akcji zaznaczenia „Zaznaczono: N".

**Faza 5 — panel podglądu (1–2 dni).** Po prawej: miniatura/ikona, nazwa, rozmiar, data, ścieżka,
przyciski Otwórz/Kopiuj. (Bez „AI Wgląd" — to osobny temat, patrz niżej.)

**Faza 6 — integracja i pakowanie (2 dni).** Menu ☰ (część akcji może wołać `thunar`/`Thunar` dla
bulk-rename i UCA), AppImage (reużywamy istniejące skrypty: mostek gvfs, launcher, font, samoaktualizacja),
release.

**Funkcje AI (poza planem wyglądu):** AUTO-KOLEKCJE, „Indeks AI", „Wgląd" wymagają realnego
indeksatora plików i (opcjonalnie) modelu. To osobny projekt — można je zasymulować regułami
(kolekcje = filtry po typie/rozmiarze/dacie: „Zrzuty ekranu", „Faktury", „Duże pliki >100 MB"),
bez AI. To realistyczne i warto zrobić w Fazie 1 jako „AUTO-KOLEKCJE" oparte na regułach.

## 4. Co zostaje z dotychczasowej pracy

Niezależnie od drogi B/C **nie marnujemy** dotychczasowego: motyw NOVA (kolory, font Space Grotesk),
etykiety kolorów (metadane gvfs), łańcuch terminali, mostek gvfs/launcher w AppImage, samoaktualizacja,
skrypty budowania — wszystko to przenosi się do nowego shella.

## 5. Rekomendacja

**Droga B.** Daje realnie „to jest NOVA" bez porzucania dojrzałych operacji plikowych, i pozwala
zachować całą infrastrukturę (AppImage, aktualizacje, motywy). Droga A już się wyczerpała
(widać po zrzutach). Droga C to najładniej, ale to pisanie menedżera plików od zera — sensowna tylko,
jeśli Thunar przestaje być wymogiem.
