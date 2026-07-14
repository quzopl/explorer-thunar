#!/usr/bin/env python3
"""Explorer 2.0 — NOVA shell na GTK4 + libadwaita.

Odwzorowuje mockup "Redesign Explorer Thunar UX": karty-kafelki (GtkGridView
z fabryką — realne widżety per plik, wirtualizowane), pigułkowy sidebar z
kartami urządzeń i mapą dysku, panel podglądu, breadcrumbs, Ctrl+K. Operacje
plikowe przez GIO (kolejna faza). Wersja 2.0.1.
"""
import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, GObject, Pango

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = "2.0.1"

# content-type -> klasa CSS odcienia miniatury
TINTS = [
    (("inode/directory",), "tint-dir"),
    (("application/pdf",), "tint-pdf"),
    (("application/zip", "application/x-tar", "application/x-compressed",
      "application/gzip", "application/x-7z"), "tint-arch"),
    (("application/vnd.openxmlformats-officedocument.wordprocessingml",
      "application/msword", "application/vnd.oasis.opendocument.text"), "tint-doc"),
    (("application/vnd.openxmlformats-officedocument.spreadsheetml",
      "application/vnd.oasis.opendocument.spreadsheet"), "tint-sheet"),
    (("image/",), "tint-img"),
    (("video/",), "tint-video"),
    (("audio/",), "tint-audio"),
    (("text/x-", "application/x-shellscript", "application/javascript",
      "text/x-python", "text/x-csrc"), "tint-code"),
    (("text/",), "tint-text"),
]

COLLECTIONS = [
    ("Zrzuty ekranu", "#34D399", lambda n, t, s: n.lower().startswith(("screenshot", "zrzut"))),
    ("Faktury i umowy", "#F59E0B", lambda n, t, s: any(k in n.lower() for k in ("faktur", "invoice", "umow"))),
    ("Kod źródłowy", "#5CE1E6", lambda n, t, s: ('.' in n and n.rsplit('.', 1)[-1].lower() in
                                                 ("py", "c", "h", "js", "ts", "sh", "rs", "go", "css", "html"))),
    ("Duże pliki (>100 MB)", "#8B7CFF", lambda n, t, s: s > 100 * 1024 * 1024),
]


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def tint_class(ctype):
    ctype = ctype or ""
    for prefixes, cls in TINTS:
        if any(ctype.startswith(p) for p in prefixes):
            return cls
    return "tint-text"


class FileItem(GObject.Object):
    __gtype_name__ = "FileItem"

    def __init__(self, info, gfile):
        super().__init__()
        self.info = info
        self.gfile = gfile

    @property
    def is_dir(self):
        return self.info.get_file_type() == Gio.FileType.DIRECTORY


class NovaWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Explorer")
        self.set_default_size(1500, 900)
        self.add_css_class("nova-root")
        self.path = GLib.get_home_dir()
        self.history = [self.path]
        self.hist_i = 0
        self.store = Gio.ListStore(item_type=FileItem)
        self.all_items = []
        self.monitor = None

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)
        root.append(self._build_header())

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True)
        root.append(body)
        body.append(self._build_sidebar())

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center.add_css_class("nova-content")
        center.set_hexpand(True)
        self.selbar = self._build_selbar()
        center.append(self.selbar)
        center.append(self._build_grid())
        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("nova-status")
        center.append(self.status)
        body.append(center)

        body.append(self._build_preview())

        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self.on_key)
        self.add_controller(key)

        self.load_dir(self.path)

    # ——— header ———
    def _build_header(self):
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        h.add_css_class("nova-header")
        badge = Gtk.Label(label="N")
        badge.add_css_class("nova-logo-badge")
        h.append(badge)
        logo = Gtk.Label(label="Explorer")
        logo.add_css_class("nova-logo")
        h.append(logo)
        for icon, cb in (("go-previous-symbolic", self.go_back),
                         ("go-next-symbolic", self.go_fwd),
                         ("go-up-symbolic", self.go_up),
                         ("go-home-symbolic", lambda *_: self.load_dir(GLib.get_home_dir()))):
            b = Gtk.Button.new_from_icon_name(icon)
            b.add_css_class("nova-navbtn")
            b.connect("clicked", cb)
            h.append(b)
        self.crumbs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        self.crumbs.add_css_class("nova-crumbs")
        h.append(self.crumbs)

        h.append(Gtk.Box(hexpand=True))

        sb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sb.add_css_class("nova-search")
        sb.append(Gtk.Image.new_from_icon_name("system-search-symbolic"))
        self.search = Gtk.Entry()
        self.search.set_placeholder_text("Szukaj lub wpisz polecenie")
        self.search.set_width_chars(22)
        self.search.set_has_frame(False)
        self.search.connect("changed", self.on_search)
        sb.append(self.search)
        kbd = Gtk.Label(label="Ctrl K")
        kbd.add_css_class("nova-kbd")
        sb.append(kbd)
        h.append(sb)

        seg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        seg.add_css_class("nova-seg")
        for icon, active in (("view-grid-symbolic", True), ("view-list-symbolic", False)):
            b = Gtk.Button.new_from_icon_name(icon)
            if active:
                b.add_css_class("active")
            seg.append(b)
        h.append(seg)

        dots = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        for cls, cb in (("min", lambda *_: self.minimize()),
                        ("max", self._toggle_max),
                        ("close", lambda *_: self.close())):
            d = Gtk.Button()
            d.add_css_class("nova-dot")
            d.add_css_class(cls)
            d.set_size_request(13, 13)
            d.connect("clicked", cb)
            dots.append(d)
        h.append(dots)
        return h

    def _toggle_max(self, *_):
        self.unmaximize() if self.is_maximized() else self.maximize()

    # ——— sidebar ———
    def _build_sidebar(self):
        sb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sb.add_css_class("nova-sidebar")
        sb.set_size_request(240, -1)
        scr = Gtk.ScrolledWindow(vexpand=True)
        scr.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scr.set_child(inner)
        sb.append(scr)

        inner.append(self._section("MIEJSCA"))
        places = Gtk.ListBox()
        places.add_css_class("nova-list")
        places.set_selection_mode(Gtk.SelectionMode.SINGLE)
        rows = [("Dom", "user-home-symbolic", GLib.get_home_dir())]
        for gdir, icon in ((GLib.UserDirectory.DIRECTORY_DOCUMENTS, "folder-documents-symbolic"),
                           (GLib.UserDirectory.DIRECTORY_PICTURES, "folder-pictures-symbolic"),
                           (GLib.UserDirectory.DIRECTORY_MUSIC, "folder-music-symbolic"),
                           (GLib.UserDirectory.DIRECTORY_VIDEOS, "folder-videos-symbolic"),
                           (GLib.UserDirectory.DIRECTORY_DOWNLOAD, "folder-download-symbolic")):
            p = GLib.get_user_special_dir(gdir)
            if p and os.path.isdir(p):
                rows.append((os.path.basename(p), icon, p))
        for name, icon, p in rows:
            places.append(self._nav_row(name, icon, p))
        places.connect("row-activated", lambda lb, row: self.load_dir(row._path))
        inner.append(places)

        sec = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sec.append(self._section("AUTO-KOLEKCJE"))
        ai = Gtk.Label(label="AI", valign=Gtk.Align.CENTER)
        ai.add_css_class("nova-section-ai")
        sec.append(ai)
        inner.append(sec)
        col = Gtk.ListBox()
        col.add_css_class("nova-list")
        col.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for label, dot, pred in COLLECTIONS:
            col.append(self._coll_row(label, dot, pred))
        col.connect("row-activated", lambda lb, row: self.load_collection(row._pred, row._label))
        inner.append(col)

        inner.append(self._section("URZĄDZENIA"))
        for name, path in self._devices():
            inner.append(self._device_card(name, path))

        inner.append(self._section("MAPA DYSKU"))
        inner.append(self._disk_map())
        return sb

    def _section(self, text):
        l = Gtk.Label(label=text, xalign=0)
        l.add_css_class("nova-section")
        return l

    def _nav_row(self, name, icon, path):
        row = Gtk.ListBoxRow()
        row.add_css_class("nova-row")
        row._path = path
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        img = Gtk.Image.new_from_icon_name(icon)
        img.add_css_class("nova-row-icon")
        box.append(img)
        box.append(Gtk.Label(label=name, xalign=0))
        row.set_child(box)
        return row

    def _coll_row(self, label, dot, pred):
        row = Gtk.ListBoxRow()
        row.add_css_class("nova-row")
        row._pred = pred
        row._label = label
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        d = Gtk.DrawingArea()
        d.set_size_request(8, 8)
        d.set_valign(Gtk.Align.CENTER)
        rgba = Gdk.RGBA(); rgba.parse(dot)
        d.set_draw_func(lambda area, cr, w, h, c=rgba:
                        (cr.set_source_rgba(c.red, c.green, c.blue, 1),
                         cr.arc(w/2, h/2, min(w, h)/2, 0, 6.2832), cr.fill()))
        box.append(d)
        box.append(Gtk.Label(label=label, xalign=0))
        row.set_child(box)
        return row

    def _devices(self):
        devs = [("System", "/")]
        for m in Gio.VolumeMonitor.get().get_mounts():
            root = m.get_root()
            if root and root.is_native() and root.get_path():
                devs.append((m.get_name(), root.get_path()))
        seen, out = set(), []
        for n, p in devs:
            if p not in seen:
                seen.add(p); out.append((n, p))
        return out[:5]

    def _usage(self, path):
        try:
            info = Gio.File.new_for_path(path).query_filesystem_info(
                "filesystem::size,filesystem::used", None)
            size = info.get_attribute_uint64("filesystem::size")
            used = info.get_attribute_uint64("filesystem::used")
            if size:
                return used, size, int(round(used * 100 / size))
        except GLib.Error:
            pass
        return 0, 0, -1

    def _device_card(self, name, path):
        used, size, pct = self._usage(path)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class("nova-devcard")
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        nm = Gtk.Label(label=name, xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END)
        nm.add_css_class("nova-dev-name")
        top.append(nm)
        pc = Gtk.Label(label=f"{pct}%" if pct >= 0 else "—")
        pc.add_css_class("nova-dev-pct")
        top.append(pc)
        card.append(top)
        lb = Gtk.LevelBar.new_for_interval(0, 100)
        lb.add_css_class("acc")
        lb.set_value(pct if pct >= 0 else 0)
        card.append(lb)
        if size:
            sub = Gtk.Label(label=f"{human_size(used)} z {human_size(size)}", xalign=0)
            sub.add_css_class("nova-dev-sub")
            card.append(sub)
        click = Gtk.GestureClick()
        click.connect("released", lambda *_: self.load_dir(path))
        card.add_controller(click)
        return card

    def _disk_map(self):
        segs = [("#5CE1E6", 18), ("#8B7CFF", 34), ("#F472B6", 12), ("#232d45", 36)]
        area = Gtk.DrawingArea()
        area.set_size_request(-1, 10)
        area.set_margin_top(4); area.set_margin_start(6); area.set_margin_end(6)

        def draw(a, cr, w, h, segs=segs):
            total = sum(s[1] for s in segs)
            x = 0.0
            r = 5
            for c, wt in segs:
                sw = w * wt / total
                rgba = Gdk.RGBA(); rgba.parse(c)
                cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 1)
                cr.rectangle(x, 0, sw, h); cr.fill()
                x += sw
        area.set_draw_func(draw)
        return area

    # ——— selection bar ———
    def _build_selbar(self):
        rev = Gtk.Revealer()
        rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.add_css_class("nova-selbar")
        self.sel_label = Gtk.Label(label="Zaznaczono: 0", xalign=0, hexpand=True)
        box.append(self.sel_label)
        for label, extra in (("Kopiuj", "primary"), ("Przenieś", None), ("Usuń", "danger")):
            b = Gtk.Button(label=label)
            b.add_css_class("nova-pillbtn")
            if extra:
                b.add_css_class(extra)
            box.append(b)
        rev.set_child(box)
        return rev

    # ——— grid (GtkGridView z fabryką) ———
    def _build_grid(self):
        self.selection = Gtk.MultiSelection(model=self.store)
        self.selection.connect("selection-changed", lambda *_: self.on_select())
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._tile_setup)
        factory.connect("bind", self._tile_bind)
        self.grid = Gtk.GridView(model=self.selection, factory=factory)
        self.grid.add_css_class("nova-grid")
        self.grid.set_max_columns(12)
        self.grid.set_min_columns(2)
        self.grid.connect("activate", self.on_activate)
        scr = Gtk.ScrolledWindow(vexpand=True)
        scr.set_child(self.grid)
        return scr

    def _tile_setup(self, factory, item):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.add_css_class("nova-tile")
        box.set_size_request(128, -1)
        thumb = Gtk.Overlay()
        bg = Gtk.Box()
        bg.add_css_class("nova-thumb")
        img = Gtk.Image()
        img.set_pixel_size(46)
        img.set_valign(Gtk.Align.CENTER)
        img.set_halign(Gtk.Align.CENTER)
        thumb.set_child(bg)
        thumb.add_overlay(img)
        name = Gtk.Label(xalign=0.5, ellipsize=Pango.EllipsizeMode.MIDDLE)
        name.set_max_width_chars(14)
        name.add_css_class("nova-tile-name")
        sub = Gtk.Label()
        sub.add_css_class("nova-tile-sub")
        box.append(thumb); box.append(name); box.append(sub)
        box._bg = bg; box._img = img; box._name = name; box._sub = sub
        item.set_child(box)

    def _tile_bind(self, factory, item):
        it = item.get_item()
        box = item.get_child()
        info = it.info
        for c in list(box._bg.get_css_classes()):
            if c.startswith("tint-"):
                box._bg.remove_css_class(c)
        box._bg.add_css_class(tint_class(info.get_content_type()))
        icon = info.get_icon()
        if icon:
            box._img.set_from_gicon(icon)
        box._name.set_text(info.get_display_name())
        box._sub.set_text("" if it.is_dir else human_size(info.get_size()))

    # ——— preview ———
    def _build_preview(self):
        p = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        p.add_css_class("nova-preview")
        p.set_size_request(300, -1)
        p.append(self._section("PODGLĄD"))
        self.prev_thumb = Gtk.Box()
        self.prev_thumb.add_css_class("nova-prev-thumb")
        self.prev_thumb.set_size_request(-1, 150)
        p.append(self.prev_thumb)
        self.prev_title = Gtk.Label(label="Wybierz plik", xalign=0,
                                    ellipsize=Pango.EllipsizeMode.MIDDLE)
        self.prev_title.add_css_class("nova-prev-title")
        p.append(self.prev_title)
        self.prev_grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        p.append(self.prev_grid)
        return p

    def _set_preview(self, it):
        info, gfile = it.info, it.gfile
        child = self.prev_grid.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.prev_grid.remove(child)
            child = nxt
        self.prev_title.set_text(info.get_display_name())
        rows = [("Rozmiar", human_size(info.get_size()) if not it.is_dir else "folder"),
                ("Typ", info.get_content_type() or "—"),
                ("Ścieżka", gfile.get_path() or "")]
        mt = info.get_modification_date_time()
        if mt:
            rows.insert(1, ("Zmieniono", mt.format("%d.%m.%Y %H:%M")))
        for i, (k, v) in enumerate(rows):
            kl = Gtk.Label(label=k, xalign=0); kl.add_css_class("nova-prev-k")
            vl = Gtk.Label(label=v, xalign=1, hexpand=True,
                           ellipsize=Pango.EllipsizeMode.MIDDLE)
            vl.add_css_class("nova-prev-v")
            self.prev_grid.attach(kl, 0, i, 1, 1)
            self.prev_grid.attach(vl, 1, i, 1, 1)

    # ——— listing / nav ———
    def load_dir(self, path, push=True):
        self.path = path
        if push:
            self.history = self.history[:self.hist_i + 1] + [path]
            self.hist_i = len(self.history) - 1
        self._render_crumbs()
        try:
            gf = Gio.File.new_for_path(path)
            en = gf.enumerate_children("standard::*,time::modified",
                                       Gio.FileQueryInfoFlags.NONE, None)
        except GLib.Error as e:
            self.status.set_text(f"Błąd: {e.message}")
            return
        items = []
        info = en.next_file(None)
        while info:
            if not info.get_is_hidden():
                items.append(FileItem(info, gf.get_child(info.get_name())))
            info = en.next_file(None)
        items.sort(key=lambda it: (not it.is_dir, it.info.get_display_name().lower()))
        self.all_items = items
        self._fill(items)
        self._watch(gf)
        nd = sum(1 for it in items if it.is_dir)
        self.status.set_markup(
            f"{len(items)} elementów · {nd} folderów · {len(items)-nd} plików"
            f"    <span foreground='#34D399'>●</span> Indeks aktualny")

    def _watch(self, gf):
        if self.monitor:
            self.monitor.cancel()
        try:
            self.monitor = gf.monitor_directory(Gio.FileMonitorFlags.NONE, None)
            self.monitor.connect("changed", lambda *a: self.load_dir(self.path, push=False))
        except GLib.Error:
            self.monitor = None

    def load_collection(self, pred, label):
        matches = [it for it in self.all_items
                   if self._safe_pred(pred, it)]
        self._render_crumbs(virtual=label)
        self._fill(matches)
        self.status.set_text("AUTO-KOLEKCJA „%s” — %d elementów w tym folderze"
                             % (label, len(matches)))

    def _safe_pred(self, pred, it):
        try:
            return pred(it.info.get_display_name(), it.info.get_content_type() or "",
                        it.info.get_size())
        except Exception:
            return False

    def _fill(self, items):
        self.store.remove_all()
        for it in items:
            self.store.append(it)

    def _render_crumbs(self, virtual=None):
        child = self.crumbs.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.crumbs.remove(child)
            child = nxt
        home = GLib.get_home_dir()
        parts, p = [], self.path
        if p == home or p.startswith(home + "/"):
            parts.append(("Dom", home)); acc = home
            for seg in [s for s in p[len(home):].split("/") if s]:
                acc = os.path.join(acc, seg); parts.append((seg, acc))
        else:
            parts.append(("/", "/")); acc = "/"
            for seg in [s for s in p.split("/") if s]:
                acc = os.path.join(acc, seg); parts.append((seg, acc))
        if virtual:
            parts.append((virtual, None))
        for i, (label, target) in enumerate(parts):
            if i:
                sep = Gtk.Label(label="›")
                sep.add_css_class("nova-crumb-sep")
                self.crumbs.append(sep)
            b = Gtk.Button(label=label)
            b.add_css_class("nova-crumb")
            if i == len(parts) - 1:
                b.add_css_class("active")
            if target:
                b.connect("clicked", lambda _b, t=target: self.load_dir(t))
            self.crumbs.append(b)

    # ——— events ———
    def on_activate(self, grid, pos):
        it = self.store.get_item(pos)
        if it.is_dir:
            self.load_dir(it.gfile.get_path())
        else:
            Gio.AppInfo.launch_default_for_uri(it.gfile.get_uri(), None)

    def on_select(self):
        sel = self.selection.get_selection()
        n = sel.get_size()
        self.selbar.set_reveal_child(n > 0)
        self.sel_label.set_text(f"Zaznaczono: {n}")
        if n >= 1:
            self._set_preview(self.store.get_item(sel.get_nth(n - 1)))

    def on_search(self, entry):
        q = entry.get_text().lower()
        if not q:
            self._fill(self.all_items)
        else:
            self._fill([it for it in self.all_items
                        if q in it.info.get_display_name().lower()])

    def on_key(self, ctrl, keyval, keycode, state):
        if state & Gdk.ModifierType.CONTROL_MASK and keyval in (Gdk.KEY_k, Gdk.KEY_K):
            self.search.grab_focus()
            return True
        if keyval == Gdk.KEY_BackSpace and not self.search.has_focus():
            self.go_up()
            return True
        return False

    def go_up(self, *_):
        parent = os.path.dirname(self.path.rstrip("/")) or "/"
        if parent != self.path:
            self.load_dir(parent)

    def go_back(self, *_):
        if self.hist_i > 0:
            self.hist_i -= 1
            self.load_dir(self.history[self.hist_i], push=False)

    def go_fwd(self, *_):
        if self.hist_i < len(self.history) - 1:
            self.hist_i += 1
            self.load_dir(self.history[self.hist_i], push=False)


class NovaApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.quzopl.Explorer")

    def do_startup(self):
        Adw.Application.do_startup(self)
        css = Gtk.CssProvider()
        css.load_from_path(os.path.join(HERE, "style.css"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)

    def do_activate(self):
        NovaWindow(self).present()


if __name__ == "__main__":
    import sys
    NovaApp().run(sys.argv)
