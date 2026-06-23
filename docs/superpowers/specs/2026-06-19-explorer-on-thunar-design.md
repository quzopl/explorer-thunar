# Explorer na silniku Thunar — projekt

Data: 2026-06-19

## Cel

Zbudować menedżer plików wyglądający i działający **jak Windows Explorer**, ale
oparty na dojrzałym, bogatym w funkcje silniku **Thunar 4.20.8** (GTK3/C),
zamiast rozwijać dalej ograniczony, napisany w Pythonie/PySide6 projekt
`/mnt/swiezak/explorer`. Łatwiej dopasować gotowca niż budować od zera.

Aplikacja ma być **osobna** ("Explorer"), zainstalowana **obok** systemowego
Thunara, bez nadpisywania go ani jego konfiguracji.

## Co Thunar już ma (nie budujemy od zera)

Weryfikacja na maszynie docelowej (Manjaro, KDE Plasma, Thunar 4.20.8):

- **Miniatury + "baza" miniatur** — działa przez `tumbler 4.20.1` (zainstalowany).
  Cache wg specyfikacji freedesktop w `~/.cache/thumbnails` (już ~812 MB).
  Tysiące zdjęć w folderze = obsłużone bez własnej bazy. Brak tylko
  `ffmpegthumbnailer` (miniatury wideo) — dołożymy w Etapie 3.
- **Wyszukiwanie jak w Windows** — wbudowane (akcja `ThunarWindow/search`,
  rekurencyjne, "pisz aby szukać", Thunar 4.20).
- **Pasek ścieżki / breadcrumb, panel boczny, widok ikon/szczegółów** — już są,
  układ bliski Explorerowi.
- **GTK 3.24.52** — pełne wsparcie nowoczesnego CSS; ciemny motyw Win11 z naszego
  Pythonowego Explorera (`src/explorer/theme/dark.qss`) przeniesie się wiernie.

## Wzorzec wyglądu (z Pythonowego Explorera)

Ciemny motyw Win11: tło `#202020`, widoki `#1c1c1c`, tekst `#e6e6e6`, font
"Segoe UI"/"Noto Sans", zaokrąglone zaznaczenia (`#2f3a4a`), hover `#2c2c2c`,
własne paski przewijania (`#3a3a3a`, promień 6px). Sortowanie: foldery-najpierw
+ sortowanie naturalne. Panel dysków: "Szybki dostęp", "Ten komputer"
z woluminami `etykieta (punkt montowania)`, sekcja "Sieć".

## Podejście

Fork źródeł Thunar 4.20.8 → osobny pakiet "Explorer", z wkompilowanym na stałe:
1. motywem Win11 (GTK CSS, ciemny + jasny), ładowanym przez samą apkę niezależnie
   od motywu systemu,
2. domyślnymi ustawieniami jak Windows (foldery-najpierw, sort naturalny, widok
   ikon z miniaturami, breadcrumb, miniatury do dużego rozmiaru plików),
3. wyszukiwaniem pod `Ctrl+F` z polem w pasku narzędzi,
4. brandingiem (nazwa "Explorer", ikona, osobny `.desktop`, osobny app-id),
5. kompilacją przez `meson` → samodzielny binar `explorer`.

Łatki w C tylko tam, gdzie ustawienia/CSS nie wystarczą.

**Odrzucone alternatywy:** (a) własne miniatury/baza — tumbler już to robi;
(b) przepisywanie panelu dysków na kafelki z paskami zajętości — duży, kruchy
kod C, niepotrzebny do osiągnięcia wyglądu Explorera.

## Decyzje (potwierdzone z użytkownikiem)

- Instalacja: **osobna apka "Explorer"** obok systemowego Thunara (nie podmiana).
- Źródła: **osobny katalog poza repo** Pythonowego Explorera —
  `/mnt/swiezak/explorer-thunar` (własne repo git).
- Głębokość zmian: docelowo pełny wygląd i funkcjonalność Windows Explorera na
  silniku Thunara, z naciskiem na wyszukiwanie i miniatury.

## Dekompozycja na etapy

Każdy etap = osobny spec → plan → implementacja.

- **Etap 1 — Fundament** (ten dokument szczegółowo): pobranie źródeł 4.20.8,
  build z meson do lokalnego prefiksu, smoke test, odbrandowanie na "Explorer"
  (binar, app-id/D-Bus, `.desktop`, ikona), weryfikacja działania obok
  systemowego Thunara.
- **Etap 2 — Wygląd:** wbudowany motyw Win11 (ciemny + jasny) + domyślne
  ustawienia (sortowanie, widok, miniatury).
- **Etap 3 — Funkcje:** wyszukiwanie w stylu Windows, miniatury wideo
  (`ffmpegthumbnailer`), dopięcie skrótów klawiszowych.

---

## Etap 1 — Fundament (szczegółowo)

### Kroki

1. **Scaffold** — katalog `/mnt/swiezak/explorer-thunar`, `git init`, `.gitignore`
   na artefakty buildu (`build/`, `install/`, `thunar-src/`). (Zrobione przy
   zapisie tego speca.)
2. **Pobrać źródła** — tarball Thunar **4.20.8** (dokładnie wersja systemowa)
   z wydania XFCE, zweryfikować, rozpakować do `thunar-src/`.
3. **Build bazowy** — `meson setup build --prefix=<repo>/install`, `ninja -C build`,
   `ninja -C build install` (instalacja do katalogu, nie do `/usr`). Brakujące
   zależności-deweloperskie uzupełniamy w trakcie.
4. **Smoke test** — uruchomić zbudowany binar w trybie offscreen, potwierdzić
   start.
5. **Odbrandowanie (kluczowe dla "obok systemowego"):**
   - nazwa binarki `thunar` → `explorer`,
   - identyfikator aplikacji / nazwa D-Bus `org.xfce.Thunar` → `io.github.quzopl.Explorer`
     (bez tego nasz "explorer" rozmawiałby z działającym demonem systemowego
     Thunara zamiast być osobną instancją),
   - własny plik `.desktop` ("Explorer") + osobna ikona,
   - nazwa w oknie / "O programie".
6. **Weryfikacja izolacji** — systemowy `thunar` i nasz `explorer` startują
   równolegle, nie nadpisują sobie konfiguracji.

### Czego Etap 1 NIE robi

Żadnego motywu, sortowania, wyszukiwania, miniatur — to Etapy 2 i 3. Tu tylko
czysty, odbrandowany, kompilujący się fundament.

### Definicja sukcesu

`install/bin/explorer` uruchamia się jako osobna aplikacja (osobny app-id),
obok niezakłóconego systemowego Thunara.

### Ryzyka / uwagi

- **Zależności buildu** — Thunar wymaga nagłówków glib2, gtk3, libxfce4util,
  libxfce4ui, exo, libgudev, libnotify itd. Na Manjaro/Arch nagłówki są w
  pakietach bibliotek; brakujące dokładamy w kroku 3.
- **App-id / D-Bus** — odbrandowanie musi obejmować nazwę GApplication, inaczej
  single-instance pokieruje nas do systemowego demona. To najważniejsza zmiana
  Etapu 1.
- **Konfiguracja** — nasz "Explorer" powinien czytać/pisać własną konfigurację
  (osobny katalog Xfconf/`~/.config`), żeby nie kolidować z systemowym Thunarem.
