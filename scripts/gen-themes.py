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
        "scroll": "#21385f", "scroll_hover": "#2e4d7e"}),
    "cobalt-light": ("Cobalt · Jasny", "light", {
        "toolbar": "#ffffff", "content": "#ffffff", "sidebar": "#0e2a5e",
        "text": "#10213d", "text_dim": "#5b6b86", "header_text": "#2f6fed",
        "border": "#e2eaf7", "hover": "#eaf1fd", "pressed": "#dfeafb",
        "accent": "#2f6fed", "sel_bg": "rgba(47,111,237,.13)", "crumb_hover": "#eaf1fd",
        "field": "#f3f7fd", "field_border": "#d4e0f4",
        "statusbar": "#0e2a5e", "statusbar_text": "#aebfe0",
        "scroll": "#cdd9ee", "scroll_hover": "#aabfe2"}),
}

TEMPLATE = """/* Explorer — motyw {label} (generowane z scripts/gen-themes.py) */
* {{ font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 10pt; }}

window, .background, dialog, popover {{ background-color: {toolbar}; color: {text}; }}

treeview.view, iconview {{ background-color: {content}; color: {text}; border: none; outline: none; }}
treeview.view:hover, iconview:hover {{ background-color: {hover}; }}
treeview.view:selected, iconview:selected, iconview .cell:selected, treeview.view:selected:focus {{
  background-color: {sel_bg}; color: {text}; }}
treeview.view header button {{ background-color: {content}; color: {header_text};
  border: none; border-bottom: 1px solid {border}; padding: 5px 8px; }}
treeview.view header button:hover {{ background-color: {hover}; }}

.sidebar, .sidebar treeview.view, placessidebar, placessidebar list {{
  background-color: {sidebar}; color: {text}; }}

toolbar, headerbar, .toolbar {{ background-color: {toolbar}; color: {text};
  border: none; border-bottom: 1px solid {border}; padding: 4px 6px; }}

button {{ background-color: transparent; color: {text}; border: none; border-radius: 5px; padding: 5px 10px; }}
button:hover {{ background-color: {hover}; }}
button:active, button:checked {{ background-color: {pressed}; }}

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
notebook, notebook header {{ background-color: {toolbar}; border-color: {border}; }}
notebook tab {{ background-color: {statusbar}; color: {text_dim}; padding: 4px 10px; }}
notebook tab:checked {{ background-color: {sel_bg}; color: {text}; }}
"""


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(here, "branding", "themes")
    os.makedirs(out, exist_ok=True)
    for slug, (label, _mode, p) in PALETTES.items():
        css = TEMPLATE.format(label=label, **p)
        with open(os.path.join(out, slug + ".css"), "w") as f:
            f.write(css)
        print("zapisano", slug + ".css")


if __name__ == "__main__":
    main()
