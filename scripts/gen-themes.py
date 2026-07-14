#!/usr/bin/env python3
"""Generuje pliki GTK CSS dla Explorera z palet kolorów (port z Pythonowego
Explorera, src/explorer/theme/palettes.py). Zapisuje do branding/themes/<slug>.css.

Uruchom: python3 scripts/gen-themes.py
"""
import os

# (slug, etykieta, tryb 'dark'/'light', tokeny)
PALETTES = {
    "fluent-dark": ("Fluent · Ciemny", "dark", {
        "toolbar": "#262626", "content": "#1c1c1c", "sidebar": "#202020",
        "text": "#e8e8ea", "text_dim": "#9aa0a8", "header_text": "#9aa0a8",
        "border": "#333334", "hover": "#2c2c2d", "pressed": "#383839",
        "accent": "#4d8bff", "sel_bg": "rgba(77,139,255,.22)", "crumb_hover": "#2e333c",
        "field": "#191919", "field_border": "#3a3a3b",
        "statusbar": "#262626", "statusbar_text": "#9aa0a8",
        "scroll": "#3a3a3b", "scroll_hover": "#4c4c4e"}),
    "fluent-light": ("Fluent · Jasny", "light", {
        "toolbar": "#fafafa", "content": "#ffffff", "sidebar": "#f8f9fb",
        "text": "#1a1a1a", "text_dim": "#5d6470", "header_text": "#6a7180",
        "border": "#e8e9ec", "hover": "#eef2f8", "pressed": "#e3e9f4",
        "accent": "#2f6fed", "sel_bg": "rgba(47,111,237,.12)", "crumb_hover": "#e8effb",
        "field": "#ffffff", "field_border": "#d9dce1",
        "statusbar": "#f4f5f7", "statusbar_text": "#6a7180",
        "scroll": "#c9cdd4", "scroll_hover": "#aeb3bc"}),
    "aurora-dark": ("Aurora · Ciemny", "dark", {
        "toolbar": "#323847", "content": "#272c36", "sidebar": "#2b313d",
        "text": "#e5e9f0", "text_dim": "#aebacf", "header_text": "#aebacf",
        "border": "#3b4252", "hover": "#353d4d", "pressed": "#3f4759",
        "accent": "#88c0d0", "sel_bg": "rgba(136,192,208,.20)", "crumb_hover": "#363e4f",
        "field": "#21262f", "field_border": "#3b4252",
        "statusbar": "#2b313d", "statusbar_text": "#aebacf",
        "scroll": "#434c5e", "scroll_hover": "#4c566a"}),
    "aurora-light": ("Aurora · Jasny", "light", {
        "toolbar": "#eceff4", "content": "#ffffff", "sidebar": "#e9edf4",
        "text": "#2e3440", "text_dim": "#4c566a", "header_text": "#4c566a",
        "border": "#dbe1ea", "hover": "#e3e9f1", "pressed": "#d8e0ec",
        "accent": "#5e81ac", "sel_bg": "rgba(94,129,172,.17)", "crumb_hover": "#e0e7f0",
        "field": "#ffffff", "field_border": "#d3dae4",
        "statusbar": "#e5e9f0", "statusbar_text": "#4c566a",
        "scroll": "#c3ccda", "scroll_hover": "#a9b4c6"}),
    "porcelain-dark": ("Porcelain · Ciemny", "dark", {
        "toolbar": "#323234", "content": "#1e1e1e", "sidebar": "#29292b",
        "text": "#f5f5f7", "text_dim": "#98989d", "header_text": "#98989d",
        "border": "#3a3a3c", "hover": "#2e2e30", "pressed": "#37373a",
        "accent": "#3b82f6", "sel_bg": "rgba(59,130,246,.24)", "crumb_hover": "#313134",
        "field": "#1c1c1e", "field_border": "#3a3a3c",
        "statusbar": "#28282a", "statusbar_text": "#98989d",
        "scroll": "#3f3f42", "scroll_hover": "#525256"}),
    "porcelain-light": ("Porcelain · Jasny", "light", {
        "toolbar": "#f6f6f6", "content": "#ffffff", "sidebar": "#f4f5f7",
        "text": "#1d1d1f", "text_dim": "#86868b", "header_text": "#86868b",
        "border": "#e6e6e8", "hover": "#f0f0f3", "pressed": "#e8e8ec",
        "accent": "#2f6fed", "sel_bg": "rgba(47,111,237,.13)", "crumb_hover": "#ececef",
        "field": "#ffffff", "field_border": "#dcdce0",
        "statusbar": "#f6f6f6", "statusbar_text": "#86868b",
        "scroll": "#c6c6cb", "scroll_hover": "#a8a8ae"}),
    "cobalt-dark": ("Cobalt · Ciemny", "dark", {
        "toolbar": "#101f3a", "content": "#0e1a30", "sidebar": "#0a1322",
        "text": "#e6eefc", "text_dim": "#92a3c2", "header_text": "#5b9bff",
        "border": "#1c3358", "hover": "#152844", "pressed": "#1b3253",
        "accent": "#3d7bff", "sel_bg": "rgba(61,123,255,.26)", "crumb_hover": "#162946",
        "field": "#0a1730", "field_border": "#21385f",
        "statusbar": "#070e1c", "statusbar_text": "#7e93ba",
        "scroll": "#21385f", "scroll_hover": "#2e4d7e",
        "sb_text": "#c8d6f0"}),
    "nova-dark": ("NOVA · Ciemny", "dark", {
        # kolory z mockupu NOVA: rgba wstępnie zmieszane do kryjących
        # (półprzezroczyste tła potrafią zostawiać czarne dziury w GTK);
        # tokeny glow/sel_border włączają dodatkową warstwę stylu NOVA
        "toolbar": "#070A12", "content": "#070A12", "sidebar": "#0C111E",
        "text": "#E7EDFF", "text_dim": "#8A94B8", "header_text": "#8A94B8",
        "border": "#1B2338", "hover": "#141B2A", "pressed": "#1D2740",
        "accent": "#5CE1E6", "sel_bg": "#16333B", "crumb_hover": "#161E30",
        "field": "#101728", "field_border": "#28334F",
        "statusbar": "#070A12", "statusbar_text": "#8A94B8",
        "scroll": "#232D45", "scroll_hover": "#3A4763",
        "sel_border": "#306E78", "glow": "rgba(92,225,230,.30)"}),
    "nova-light": ("NOVA · Jasny", "light", {
        "toolbar": "#EDF0F8", "content": "#FFFFFF", "sidebar": "#F4F6FC",
        "text": "#131933", "text_dim": "#5B6488", "header_text": "#5B6488",
        "border": "#DEE2E9", "hover": "#F1F2F5", "pressed": "#E8EBF0",
        "accent": "#0E8C9C", "sel_bg": "#E0F0F2", "crumb_hover": "#ECF6F7",
        "field": "#FFFFFF", "field_border": "#CDD2E0",
        "statusbar": "#EDF0F8", "statusbar_text": "#5B6488",
        "scroll": "#C7CEE2", "scroll_hover": "#A9B3D2",
        "sel_border": "#93CBD2", "glow": "rgba(14,140,156,.22)"}),
    "cobalt-light": ("Cobalt · Jasny", "light", {
        "toolbar": "#ffffff", "content": "#ffffff", "sidebar": "#0e2a5e",
        "text": "#10213d", "text_dim": "#5b6b86", "header_text": "#2f6fed",
        "border": "#e2eaf7", "hover": "#eaf1fd", "pressed": "#dfeafb",
        "accent": "#2f6fed", "sel_bg": "rgba(47,111,237,.13)", "crumb_hover": "#eaf1fd",
        "field": "#f3f7fd", "field_border": "#d4e0f4",
        "statusbar": "#0e2a5e", "statusbar_text": "#aebfe0",
        "scroll": "#cdd9ee", "scroll_hover": "#aabfe2",
        "sb_text": "#dbe6fa", "sb_hover": "rgba(255,255,255,.08)"}),
}

TEMPLATE = """/* Explorer — motyw {label} (generowane z scripts/gen-themes.py) */
* {{ font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 10pt; }}

window, .background, dialog, popover {{ background-color: {toolbar}; color: {text}; }}

.standard-view, .standard-view .view, .standard-view .view text,
treeview.view, iconview {{ background-color: {content}; color: {text}; border: none; outline: none; }}
.standard-view .view:hover, treeview.view:hover, iconview:hover {{ background-color: {hover}; }}
.standard-view .view:selected, treeview.view:selected, iconview:selected, iconview .cell:selected {{
  background-color: {sel_bg}; color: {text}; }}
treeview.view header button {{ background-color: {content}; color: {header_text};
  border: none; border-bottom: 1px solid {border}; padding: 5px 8px; }}
treeview.view header button:hover {{ background-color: {hover}; }}

.sidebar, .sidebar .view, .sidebar treeview.view, placessidebar, placessidebar list {{
  background-color: {sidebar}; color: {sb_text}; }}
.sidebar .view:hover, .sidebar treeview.view:hover {{ background-color: {sb_hover}; }}
.sidebar label {{ color: {sb_text}; }}

toolbar, headerbar, .toolbar {{ background-color: {toolbar}; color: {text};
  border: none; border-bottom: 1px solid {border}; padding: 4px 6px; }}

/* background-image/box-shadow: none — kasuje gradient/cień przycisku z
 * systemowego motywu GTK (np. Breeze-Dark na KDE), który inaczej przebija
 * jako ciemny/czarny prostokąt na aktywnym przycisku widoku. */
button {{ background-color: transparent; background-image: none; box-shadow: none;
  color: {text}; border: none; border-radius: 5px; padding: 5px 10px; }}
button:hover {{ background-color: {hover}; background-image: none; box-shadow: none; }}
button:active, button:checked {{ background-color: {pressed}; background-image: none; box-shadow: none; }}

/* aktywny przycisk widoku (ikony/szczegóły/kompakt) w pasku narzędzi —
 * subtelny akcent zamiast brzydkiego ciemnego kwadratu */
toolbar button:checked, .toolbar button:checked,
toolbar togglebutton:checked, toolbar button:active {{
  background-color: {sel_bg}; background-image: none; box-shadow: none; color: {text}; }}
toolbar button:checked:hover, .toolbar button:checked:hover {{ background-color: {hover}; }}

entry {{ background-color: {field}; color: {text}; border: 1px solid {field_border};
  border-radius: 5px; padding: 4px 8px; }}
entry:focus {{ border-color: {accent}; }}

.path-bar button, .location-bar button {{ background-color: transparent; color: {text_dim}; border-radius: 4px; padding: 3px 8px; }}
.path-bar button:hover, .location-bar button:hover {{ background-color: {crumb_hover}; color: {text}; }}

menu, .menu, popover.menu, .context-menu {{ background-color: {toolbar}; color: {text}; border: 1px solid {border}; padding: 4px; }}
menuitem {{ border-radius: 4px; padding: 6px 14px; }}
menuitem:hover, menuitem:selected {{ background-color: {hover}; color: {text}; }}
menubar {{ background-color: {toolbar}; color: {text}; }}
menubar > menuitem:hover {{ background-color: {hover}; }}
separator {{ background-color: {border}; min-height: 1px; min-width: 1px; }}

statusbar, .statusbar {{ background-color: {statusbar}; color: {statusbar_text}; border-top: 1px solid {border}; }}

scrollbar {{ background-color: {toolbar}; border: none; }}
scrollbar slider {{ background-color: {scroll}; border-radius: 6px; min-width: 8px; min-height: 30px; }}
scrollbar slider:hover {{ background-color: {scroll_hover}; }}

paned > separator {{ background-color: {border}; }}
/* zakładki: neutralne tło zamiast koloru statusbara — w jasnych paletach
 * (np. cobalt-light ze statusbarem granatowym) taby gryzły się z dialogiem */
notebook, notebook header {{ background-color: {toolbar}; border-color: {border}; }}
notebook tab {{ background-color: transparent; color: {text_dim}; padding: 4px 10px;
  border: none; }}
notebook tab:hover {{ background-color: {hover}; }}
notebook tab:checked {{ background-color: {sel_bg}; color: {text}; }}

/* tooltipy — bez tego tekst dziedziczy kolor z motywu aplikacji, a tło
 * z motywu systemowego: bywa ciemne na ciemnym */
tooltip.background, tooltip {{ background-color: {toolbar}; color: {text};
  border: 1px solid {border}; border-radius: 5px; }}
tooltip label {{ color: {text}; }}

/* pasek zajętości dysku (Właściwości dysku -> Usage) */
levelbar trough {{ background-color: {field}; border: 1px solid {field_border};
  border-radius: 4px; }}
levelbar block.filled {{ background-color: {accent}; border-radius: 4px; }}
levelbar block.empty {{ background-color: transparent; }}

/* wnętrza dialogów (Właściwości itd.) — motyw systemowy maluje stronę
 * notebooka (notebook > stack) własnym kolorem bazowym (np. białym),
 * a nasze etykiety dziedziczą jasny tekst -> nieczytelne. Kryjemy całość. */
notebook > stack {{ background-color: {toolbar}; color: {text}; }}
frame > border {{ border-color: {border}; }}
combobox cellview, combobox label {{ color: {text}; }}
textview, textview text {{ background-color: {field}; color: {text}; }}

/* wskaźniki wyboru, suwaki, przełączniki, infobary — bez jawnych reguł
 * bazowy motyw GTK (np. wymuszone w AppImage Adwaita:dark) przebija
 * ciemnymi elementami i nieczytelnym tekstem w jasnych paletach */
check, radio {{ background-color: {field}; background-image: none; box-shadow: none;
  border: 1px solid {field_border}; color: #ffffff; min-width: 14px; min-height: 14px; }}
check {{ border-radius: 3px; }}
radio {{ border-radius: 50%; }}
check:checked, radio:checked, check:indeterminate {{
  background-color: {accent}; border-color: {accent}; color: #ffffff; }}
scale trough {{ background-color: {field}; border: 1px solid {field_border};
  border-radius: 4px; min-height: 6px; }}
scale highlight {{ background-color: {accent}; border-radius: 4px; }}
scale slider {{ background-color: #ffffff; background-image: none; box-shadow: none;
  border: 1px solid {scroll}; border-radius: 50%; min-width: 16px; min-height: 16px; }}
scale marks, scale value {{ color: {text_dim}; }}
switch {{ background-color: {field}; background-image: none; border: 1px solid {field_border}; }}
switch:checked {{ background-color: {accent}; border-color: {accent}; }}
switch slider {{ background-color: #ffffff; background-image: none; box-shadow: none; }}
spinbutton {{ background-color: {field}; color: {text}; border: 1px solid {field_border}; }}
spinbutton button {{ background-color: transparent; color: {text}; border: none; }}
infobar, infobar revealer > box, infobar > revealer > box {{
  background-color: {hover}; background-image: none; color: {text}; }}
infobar label {{ color: {text}; }}
label.dim-label, .dim-label {{ color: {text_dim}; }}

/* dialog postępu kopiowania/przenoszenia — bez tego pasek postępu
 * dziedziczy wygląd z motywu systemowego i gryzie się z paletą */
progressbar trough {{ background-color: {field}; border: 1px solid {field_border};
  border-radius: 4px; min-height: 8px; }}
progressbar progress {{ background-color: {accent}; border: none; border-radius: 4px; min-height: 8px; }}

/* headerbar CSD (belka tytułu po stronie aplikacji, jak w Windows 11).
 * Selektory z klasą .titlebar i :backdrop muszą być co najmniej tak
 * specyficzne jak w motywie systemowym (Adwaita/Breeze stylują
 * ".titlebar:backdrop"), inaczej nieaktywne okno dostaje jasny pas. */
headerbar, .titlebar, headerbar.titlebar {{ background-color: {toolbar};
  background-image: none; box-shadow: none; color: {text}; border: none;
  border-bottom: 1px solid {border}; min-height: 40px; padding: 2px 6px; }}
headerbar:backdrop, .titlebar:backdrop, headerbar.titlebar:backdrop {{
  background-color: {toolbar}; background-image: none; color: {text_dim}; }}
headerbar button.titlebutton, .titlebar button.titlebutton {{
  background-color: transparent; background-image: none; box-shadow: none;
  color: {text}; border-radius: 5px; padding: 4px; min-width: 24px; min-height: 24px; }}
headerbar button.titlebutton:hover, .titlebar button.titlebutton:hover {{
  background-color: {hover}; }}
headerbar button.titlebutton:backdrop, .titlebar button.titlebutton:backdrop {{
  color: {text_dim}; }}
"""


# Warstwa języka wizualnego NOVA (mockup "Redesign Explorer Thunar UX"):
# pigułkowe kontenery, większe promienie, akcentowe ramki i poświata.
# Doklejana do palet z tokenem "glow". rgba tylko w box-shadow (bez teł!).
NOVA_EXTRA = """
/* ——— warstwa stylu NOVA: font, pigułki, promienie, poświata ——— */
* {{ font-family: "Space Grotesk", "Segoe UI", "Noto Sans", sans-serif; }}

/* przyciski okna jako kropki (traffic lights z mockupu) */
headerbar button.titlebutton, .titlebar button.titlebutton {{
  min-width: 13px; min-height: 13px; padding: 0; margin: 0 4px;
  border-radius: 50%; background-color: {scroll}; border: none; }}
headerbar button.titlebutton image, .titlebar button.titlebutton image {{
  opacity: 0; }}
headerbar button.titlebutton:hover, .titlebar button.titlebutton:hover {{
  background-color: {scroll_hover}; }}
headerbar button.titlebutton.close, .titlebar button.titlebutton.close {{
  background-color: #F45C7F; }}
headerbar button.titlebutton.close:hover, .titlebar button.titlebutton.close:hover {{
  background-color: #F87171; box-shadow: 0 0 8px {glow}; }}

entry {{ border-radius: 10px; padding: 6px 12px; }}
entry:focus {{ border-color: {accent}; box-shadow: 0 0 10px {glow}; }}
button {{ border-radius: 9px; padding: 6px 11px; }}
toolbar button:checked, .toolbar button:checked {{
  border: 1px solid {sel_border}; box-shadow: 0 0 10px {glow}; }}
.path-bar {{ background-color: {field}; border: 1px solid {field_border};
  border-radius: 10px; padding: 1px 5px; }}
.path-bar button {{ border-radius: 7px; padding: 4px 10px; color: {text_dim}; }}
.path-bar button:hover {{ color: {text}; }}
.path-bar button:checked {{ background-color: {sel_bg}; color: {text}; }}
menu, .menu, .context-menu {{ border: 1px solid {sel_border}; border-radius: 12px; padding: 6px; }}
menuitem {{ border-radius: 8px; padding: 7px 14px; }}
.standard-view .view:selected, iconview:selected, iconview .cell:selected {{ border-radius: 10px; }}
notebook tab {{ border-radius: 8px; padding: 5px 12px; }}
tooltip.background, tooltip {{ border-radius: 10px; border: 1px solid {sel_border}; }}
scrollbar slider {{ border-radius: 8px; min-width: 6px; }}
progressbar progress {{ box-shadow: 0 0 8px {glow}; }}
levelbar block.filled {{ box-shadow: 0 0 8px {glow}; }}
.sidebar, placessidebar {{ border-right: 1px solid {border}; }}
"""


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(here, "branding", "themes")
    os.makedirs(out, exist_ok=True)
    for slug, (label, _mode, p) in PALETTES.items():
        tokens = dict(p)
        tokens.setdefault("sb_text", p["text"])
        tokens.setdefault("sb_hover", p["hover"])
        css = TEMPLATE.format(label=label, **tokens)
        if "glow" in p:
            css += NOVA_EXTRA.format(**tokens)
        with open(os.path.join(out, slug + ".css"), "w") as f:
            f.write(css)
        print("zapisano", slug + ".css")


if __name__ == "__main__":
    main()
