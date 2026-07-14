# Explorer 2.0 — NOVA shell (GTK4 + libadwaita)

A purpose-built file-manager shell that implements the **"Redesign Explorer
Thunar UX" (NOVA)** mockup. This is the 2.x line: unlike the 1.x builds (a
themed Thunar fork under `../patches/`), the NOVA look cannot be reached by
theming GTK3 Thunar — its file view is `GtkIconView` and the sidebar is
`GtkTreeView`, neither of which can render card tiles or pill rows. GTK4's
`GtkGridView` (widget factories, virtualized) makes the cards possible **and**
fast on huge folders. See `../docs/NOVA-implementation-plan.md`.

## Run

```bash
python3 explorer-nova/app.py
```

Requires GTK4, libadwaita and PyGObject (`gir1.2-gtk-4.0`, `gir1.2-adw-1`,
`python3-gi`). The Space Grotesk font (in `../branding/fonts`) gives the
mockup's look; without it a sans-serif fallback is used.

## Done (phases 0-2)

- Header: logo, nav, **pill breadcrumbs**, "Szukaj / Ctrl K", view segment, traffic-light window dots.
- Sidebar: **MIEJSCA**, rule-based **AUTO-KOLEKCJE** (no AI: Zrzuty ekranu / Faktury / Kod / Duże pliki), **URZĄDZENIA** device cards with usage `GtkLevelBar`, **MAPA DYSKU** bar.
- Content: **`GtkGridView` card tiles** (typed gradient thumbnail + name + size), real widgets, virtualized.
- **Selection action bar** (Kopiuj / Przenieś / Usuń) + **metadata preview pane**.
- Navigation, breadcrumbs, live search, Ctrl+K, history, `GFileMonitor` auto-refresh — via GIO.

## Next (phases 3+)

- **File operations via GIO**: copy / move / trash / rename / delete with progress
  and overwrite handling (`g_file_copy/move/trash`), reusing the color-label gvfs
  metadata from the 1.x build.
- List view (`GtkColumnView`: NAZWA / ROZMIAR / TYP / ZMIENIONO / TAG).
- Packaging as an AppImage + self-update (reuse the 1.x gvfs-bridge / launcher /
  font / self-update scripts).
