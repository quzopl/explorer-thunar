#!/usr/bin/env python3
"""Explorer NOVA — własny shell GTK3 odwzorowujący mockup "Redesign Explorer
Thunar UX". Widok plików, sidebar, panel podglądu i operacje przez GIO.
Faza 0-2: layout kart + nawigacja + podgląd. (Operacje plikowe: kolejna faza.)
"""
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf, Pango

HERE = os.path.dirname(os.path.abspath(__file__))

# kolorowe tła kafelków wg typu (jak w mockupie)
TYPE_TINT = {
    'inode/directory': '#5CE1E6', 'application/pdf': '#F87171',
    'text/plain': '#94A3B8', 'text/markdown': '#34D399',
    'application/zip': '#F59E0B', 'application/x-tar': '#F59E0B',
    'image': '#F472B6', 'video': '#8B7CFF', 'audio': '#60A5FA',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '#60A5FA',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '#34D399',
}

# AUTO-KOLEKCJE oparte na regułach (bez AI) — (etykieta, kolor kropki, predykat)
COLLECTIONS = [
    ("Zrzuty ekranu", "#34D399", lambda n, t, s: n.lower().startswith(("screenshot", "zrzut"))),
    ("Faktury i umowy", "#F59E0B", lambda n, t, s: any(k in n.lower() for k in ("faktur", "invoice", "umowa", "umow"))),
    ("Kod źródłowy", "#5CE1E6", lambda n, t, s: n.rsplit('.', 1)[-1].lower() in ("py", "c", "h", "js", "ts", "sh", "rs", "go", "css", "html") if '.' in n else False),
    ("Duże pliki (>100 MB)", "#8B7CFF", lambda n, t, s: s > 100 * 1024 * 1024),
]


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return (f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}")
        n /= 1024


def hex_rgba(h, a):
    h = h.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def tint_for(ctype):
    if ctype in TYPE_TINT:
        return TYPE_TINT[ctype]
    for k, v in TYPE_TINT.items():
        if ctype.startswith(k):
            return v
    return '#8A94B8'


class NovaWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Explorer")
        self.set_default_size(1500, 880)
        self.set_decorated(False)  # CSD-like: własna belka
        self.get_style_context().add_class("nova-root")
        self.path = GLib.get_home_dir()
        self.history = [self.path]
        self.hist_i = 0
        self.entries = []
        self.selected = None

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)
        root.pack_start(self._build_header(), False, False, 0)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True)
        root.pack_start(body, True, True, 0)

        body.pack_start(self._build_sidebar(), False, False, 0)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center.get_style_context().add_class("nova-content")
        center.set_hexpand(True)
        self.selbar = self._build_selbar()
        center.pack_start(self.selbar, False, False, 0)
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_vexpand(True)
        self.grid = Gtk.FlowBox()
        self.grid.get_style_context().add_class("nova-grid")
        self.grid.set_valign(Gtk.Align.START)
        self.grid.set_max_children_per_line(12)
        self.grid.set_min_children_per_line(2)
        self.grid.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.grid.set_homogeneous(True)
        self.grid.connect("child-activated", self.on_activate)
        self.grid.connect("selected-children-changed", self.on_select)
        self.scroller.add(self.grid)
        center.pack_start(self.scroller, True, True, 0)
        self.status = Gtk.Label(xalign=0)
        self.status.get_style_context().add_class("nova-status")
        center.pack_start(self.status, False, False, 0)
        body.pack_start(center, True, True, 0)

        body.pack_start(self._build_preview(), False, False, 0)

        self.connect("key-press-event", self.on_key)
        self.connect("destroy", Gtk.main_quit)
        self.load_dir(self.path)

    # ——— header ———
    def _build_header(self):
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        h.get_style_context().add_class("nova-header")
        # logo
        badge = Gtk.Label(label="N")
        badge.get_style_context().add_class("nova-logo-badge")
        h.pack_start(badge, False, False, 0)
        logo = Gtk.Label(label="Explorer")
        logo.get_style_context().add_class("nova-logo")
        h.pack_start(logo, False, False, 0)
        # nawigacja
        for icon, cb in (("go-previous-symbolic", self.go_back),
                         ("go-next-symbolic", self.go_fwd),
                         ("go-up-symbolic", self.go_up),
                         ("go-home-symbolic", lambda *_: self.load_dir(GLib.get_home_dir()))):
            b = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.MENU)
            b.get_style_context().add_class("nova-navbtn")
            b.set_relief(Gtk.ReliefStyle.NONE)
            b.connect("clicked", cb)
            h.pack_start(b, False, False, 0)
        # breadcrumbs
        self.crumbs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        self.crumbs.get_style_context().add_class("nova-crumbs")
        h.pack_start(self.crumbs, False, False, 6)
        # spacer
        h.pack_start(Gtk.Box(), True, True, 0)
        # search
        sb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sb.get_style_context().add_class("nova-search")
        sb.pack_start(Gtk.Image.new_from_icon_name("system-search-symbolic", Gtk.IconSize.MENU), False, False, 0)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Szukaj lub wpisz polecenie")
        self.search.set_width_chars(22)
        self.search.connect("search-changed", self.on_search)
        sb.pack_start(self.search, False, False, 0)
        kbd = Gtk.Label(label="Ctrl K")
        kbd.get_style_context().add_class("nova-kbd")
        sb.pack_start(kbd, False, False, 0)
        h.pack_start(sb, False, False, 0)
        # segment widoku
        seg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        seg.get_style_context().add_class("nova-seg")
        for icon, active in (("view-grid-symbolic", True), ("view-list-symbolic", False)):
            b = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.MENU)
            b.set_relief(Gtk.ReliefStyle.NONE)
            if active:
                b.get_style_context().add_class("active")
            seg.pack_start(b, False, False, 0)
        h.pack_start(seg, False, False, 0)
        # kropki okna
        dots = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        for cls, cb in (("min", self.iconify), ("max", self._toggle_max), ("close", lambda *_: self.destroy())):
            d = Gtk.Button()
            d.get_style_context().add_class("nova-dot")
            d.get_style_context().add_class(cls)
            d.set_size_request(13, 13)
            d.connect("clicked", cb)
            dots.pack_start(d, False, False, 0)
        h.pack_start(dots, False, False, 6)
        return h

    def _toggle_max(self, *_):
        if self.is_maximized():
            self.unmaximize()
        else:
            self.maximize()

    # ——— sidebar ———
    def _build_sidebar(self):
        sb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sb.get_style_context().add_class("nova-sidebar")
        sb.set_size_request(240, -1)
        scr = Gtk.ScrolledWindow()
        scr.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scr.add(inner)
        sb.pack_start(scr, True, True, 0)

        inner.pack_start(self._section("MIEJSCA"), False, False, 0)
        places = Gtk.ListBox()
        places.get_style_context().add_class("nova-list")
        places.set_selection_mode(Gtk.SelectionMode.SINGLE)
        SPECIAL = [("Dom", "user-home-symbolic", GLib.get_home_dir())]
        for gdir, icon in ((GLib.UserDirectory.DIRECTORY_DOCUMENTS, "folder-documents-symbolic"),
                           (GLib.UserDirectory.DIRECTORY_PICTURES, "folder-pictures-symbolic"),
                           (GLib.UserDirectory.DIRECTORY_MUSIC, "folder-music-symbolic"),
                           (GLib.UserDirectory.DIRECTORY_VIDEOS, "folder-videos-symbolic"),
                           (GLib.UserDirectory.DIRECTORY_DOWNLOAD, "folder-download-symbolic")):
            p = GLib.get_user_special_dir(gdir)
            if p and os.path.isdir(p):
                SPECIAL.append((os.path.basename(p), icon, p))
        for name, icon, p in SPECIAL:
            places.add(self._place_row(name, icon, p))
        places.connect("row-activated", lambda lb, row: self.load_dir(row._path))
        inner.pack_start(places, False, False, 0)

        # AUTO-KOLEKCJE (reguły)
        sec = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sec.pack_start(self._section("AUTO-KOLEKCJE"), False, False, 0)
        ai = Gtk.Label(label="AI")
        ai.get_style_context().add_class("nova-section-ai")
        ai.set_valign(Gtk.Align.CENTER)
        sec.pack_start(ai, False, False, 0)
        inner.pack_start(sec, False, False, 0)
        col = Gtk.ListBox()
        col.get_style_context().add_class("nova-list")
        col.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for label, dot, pred in COLLECTIONS:
            col.add(self._collection_row(label, dot, pred))
        col.connect("row-activated", lambda lb, row: self.load_collection(row._pred, row._label))
        inner.pack_start(col, False, False, 0)

        # URZĄDZENIA — karty z zajętością
        inner.pack_start(self._section("URZĄDZENIA"), False, False, 0)
        for name, path in self._devices():
            inner.pack_start(self._device_card(name, path), False, False, 0)

        # MAPA DYSKU
        inner.pack_start(self._section("MAPA DYSKU"), False, False, 0)
        inner.pack_start(self._disk_map(), False, False, 4)
        return sb

    def _section(self, text):
        l = Gtk.Label(label=text, xalign=0)
        l.get_style_context().add_class("nova-section")
        return l

    def _place_row(self, name, icon, path):
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("nova-row")
        row._path = path
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        img = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)
        img.get_style_context().add_class("nova-row-icon")
        box.pack_start(img, False, False, 0)
        box.pack_start(Gtk.Label(label=name, xalign=0), True, True, 0)
        row.add(box)
        return row

    def _collection_row(self, label, dot, pred):
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("nova-row")
        row._pred = pred
        row._label = label
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        d = Gtk.Box()
        d.get_style_context().add_class("nova-dot-c")
        d.set_size_request(8, 8)
        css = Gtk.CssProvider()
        css.load_from_data((".nova-dot-c{background-color:%s;}" % dot).encode())
        d.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        d.set_valign(Gtk.Align.CENTER)
        box.pack_start(d, False, False, 0)
        box.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
        row.add(box)
        return row

    def _devices(self):
        devs = []
        mon = Gio.VolumeMonitor.get()
        for m in mon.get_mounts():
            root = m.get_root()
            if root and root.is_native():
                devs.append((m.get_name(), root.get_path()))
        # zawsze pokaż korzeń systemu
        devs.insert(0, ("System", "/"))
        seen, out = set(), []
        for n, p in devs:
            if p and p not in seen:
                seen.add(p)
                out.append((n, p))
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
        card.get_style_context().add_class("nova-devcard")
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        nm = Gtk.Label(label=name, xalign=0)
        nm.get_style_context().add_class("nova-dev-name")
        nm.set_ellipsize(Pango.EllipsizeMode.END)
        top.pack_start(nm, True, True, 0)
        pc = Gtk.Label(label=(f"{pct}%" if pct >= 0 else "—"))
        pc.get_style_context().add_class("nova-dev-pct")
        top.pack_start(pc, False, False, 0)
        card.pack_start(top, False, False, 0)
        lb = Gtk.LevelBar()
        lb.get_style_context().add_class("acc")
        lb.set_min_value(0); lb.set_max_value(100)
        lb.set_value(pct if pct >= 0 else 0)
        card.pack_start(lb, False, False, 0)
        if size:
            sub = Gtk.Label(label=f"{human_size(used)} z {human_size(size)}", xalign=0)
            sub.get_style_context().add_class("nova-dev-sub")
            card.pack_start(sub, False, False, 0)
        card._path = path
        ev = Gtk.EventBox()
        ev.add(card)
        ev.connect("button-press-event", lambda *_: self.load_dir(path))
        return ev

    def _disk_map(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        bar.get_style_context().add_class("nova-map")
        bar.set_size_request(-1, 10)
        segs = [("#5CE1E6", 18), ("#8B7CFF", 34), ("#F472B6", 12), ("#232d45", 36)]
        for i, (c, w) in enumerate(segs):
            b = Gtk.Box()
            b.set_hexpand(True)
            b.set_size_request(int(w * 2), 10)
            css = Gtk.CssProvider()
            radius = ("border-top-left-radius:5px;border-bottom-left-radius:5px;" if i == 0 else
                      "border-top-right-radius:5px;border-bottom-right-radius:5px;" if i == len(segs)-1 else "")
            css.load_from_data(("box{background-color:%s;%s}" % (c, radius)).encode())
            b.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            bar.pack_start(b, True, True, 0)
        return bar

    # ——— selection bar ———
    def _build_selbar(self):
        rev = Gtk.Revealer()
        rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.get_style_context().add_class("nova-toolbar-sel")
        self.sel_label = Gtk.Label(label="Zaznaczono: 0", xalign=0)
        box.pack_start(self.sel_label, True, True, 4)
        for label, primary in (("Kopiuj", True), ("Przenieś", False), ("Usuń", False)):
            b = Gtk.Button(label=label)
            b.get_style_context().add_class("nova-pillbtn")
            if primary:
                b.get_style_context().add_class("primary")
            box.pack_start(b, False, False, 0)
        rev.add(box)
        return rev

    # ——— preview ———
    def _build_preview(self):
        self.preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.preview.get_style_context().add_class("nova-preview")
        self.preview.set_size_request(300, -1)
        self.preview.pack_start(self._section("PODGLĄD"), False, False, 0)
        self.prev_thumb = Gtk.Box()
        self.prev_thumb.get_style_context().add_class("nova-prev-thumb")
        self.prev_thumb.set_size_request(-1, 150)
        self.preview.pack_start(self.prev_thumb, False, False, 0)
        self.prev_title = Gtk.Label(label="Wybierz plik", xalign=0)
        self.prev_title.get_style_context().add_class("nova-prev-title")
        self.prev_title.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.preview.pack_start(self.prev_title, False, False, 0)
        self.prev_grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        self.preview.pack_start(self.prev_grid, False, False, 6)
        return self.preview

    def _set_preview(self, info, gfile):
        for c in self.prev_grid.get_children():
            self.prev_grid.remove(c)
        self.prev_title.set_text(info.get_display_name())
        rows = [("Rozmiar", human_size(info.get_size())),
                ("Typ", info.get_content_type() or "—"),
                ("Ścieżka", gfile.get_path() or "")]
        mt = info.get_modification_date_time()
        if mt:
            rows.insert(1, ("Zmieniono", mt.format("%d.%m.%Y %H:%M")))
        for i, (k, v) in enumerate(rows):
            kl = Gtk.Label(label=k, xalign=0); kl.get_style_context().add_class("nova-prev-k")
            vl = Gtk.Label(label=v, xalign=1); vl.get_style_context().add_class("nova-prev-v")
            vl.set_ellipsize(Pango.EllipsizeMode.MIDDLE); vl.set_hexpand(True)
            self.prev_grid.attach(kl, 0, i, 1, 1)
            self.prev_grid.attach(vl, 1, i, 1, 1)
        self.prev_grid.show_all()

    # ——— tiles / listing ———
    def _tile(self, info, gfile):
        child = Gtk.FlowBoxChild()
        child._info = info
        child._gfile = gfile
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.get_style_context().add_class("nova-tile")
        box.set_size_request(120, -1)
        thumb = Gtk.Box()
        thumb.get_style_context().add_class("nova-tile-thumb")
        tint = tint_for(info.get_content_type() or "")
        css = Gtk.CssProvider()
        css.load_from_data(("box{background-image:radial-gradient(120%% 120%% at 20%% 0%%, %s, #101728);}" % hex_rgba(tint, 0.22)).encode())
        thumb.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        thumb.set_size_request(-1, 74)
        icon = info.get_icon()
        img = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG) if icon else Gtk.Image()
        img.set_pixel_size(46)
        img.set_valign(Gtk.Align.CENTER)
        thumb_overlay = Gtk.Overlay()
        thumb_overlay.add(thumb)
        thumb_overlay.add_overlay(img)
        box.pack_start(thumb_overlay, False, False, 0)
        name = Gtk.Label(label=info.get_display_name(), xalign=0.5)
        name.get_style_context().add_class("nova-tile-name")
        name.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        name.set_max_width_chars(14)
        box.pack_start(name, False, False, 0)
        if info.get_file_type() != Gio.FileType.DIRECTORY:
            sub = Gtk.Label(label=human_size(info.get_size()))
            sub.get_style_context().add_class("nova-tile-sub")
            box.pack_start(sub, False, False, 0)
        child.add(box)
        return child

    def load_dir(self, path, push=True):
        self.path = path
        if push:
            self.history = self.history[:self.hist_i + 1] + [path]
            self.hist_i = len(self.history) - 1
        self._render_crumbs()
        try:
            gf = Gio.File.new_for_path(path)
            en = gf.enumerate_children(
                "standard::*,time::modified", Gio.FileQueryInfoFlags.NONE, None)
        except GLib.Error as e:
            self.status.set_text(f"Błąd: {e.message}")
            return
        self.entries = []
        info = en.next_file(None)
        while info:
            if not info.get_is_hidden():
                self.entries.append((info, gf.get_child(info.get_name())))
            info = en.next_file(None)
        self.entries.sort(key=lambda e: (e[0].get_file_type() != Gio.FileType.DIRECTORY,
                                         e[0].get_display_name().lower()))
        self._populate(self.entries)
        n_dirs = sum(1 for i, _ in self.entries if i.get_file_type() == Gio.FileType.DIRECTORY)
        n_files = len(self.entries) - n_dirs
        self.status.set_markup(
            f"{len(self.entries)} elementów · {n_dirs} folderów · {n_files} plików"
            f"    <span foreground='#34D399'>●</span> Indeks aktualny")

    def load_collection(self, pred, label):
        # przeszukaj bieżący katalog rekurencyjnie (płytko: bieżący + 1 poziom)
        matches = []
        for info, gfile in self.entries:
            n = info.get_display_name()
            s = info.get_size()
            t = info.get_content_type() or ""
            try:
                if pred(n, t, s):
                    matches.append((info, gfile))
            except Exception:
                pass
        self._render_crumbs(virtual=label)
        self._populate(matches)
        self.status.set_text("AUTO-KOLEKCJA „%s” — %d elementów w tym folderze"
                             % (label, len(matches)))

    def _populate(self, entries):
        for c in self.grid.get_children():
            self.grid.remove(c)
        for info, gfile in entries:
            self.grid.add(self._tile(info, gfile))
        self.grid.show_all()

    def _render_crumbs(self, virtual=None):
        for c in self.crumbs.get_children():
            self.crumbs.remove(c)
        parts = []
        p = self.path
        home = GLib.get_home_dir()
        if p == home or p.startswith(home + "/"):
            parts.append(("Dom", home))
            rest = p[len(home):].strip("/")
            acc = home
            for seg in [s for s in rest.split("/") if s]:
                acc = os.path.join(acc, seg)
                parts.append((seg, acc))
        else:
            acc = "/"
            parts.append(("/", "/"))
            for seg in [s for s in p.split("/") if s]:
                acc = os.path.join(acc, seg)
                parts.append((seg, acc))
        if virtual:
            parts.append((virtual, None))
        for i, (label, target) in enumerate(parts):
            if i:
                sep = Gtk.Label(label="›")
                sep.get_style_context().add_class("nova-crumb-sep")
                self.crumbs.pack_start(sep, False, False, 0)
            b = Gtk.Button(label=label)
            b.get_style_context().add_class("nova-crumb")
            b.set_relief(Gtk.ReliefStyle.NONE)
            if i == len(parts) - 1:
                b.get_style_context().add_class("active")
            if target:
                b.connect("clicked", lambda _b, t=target: self.load_dir(t))
            self.crumbs.pack_start(b, False, False, 0)
        self.crumbs.show_all()

    # ——— events ———
    def on_activate(self, box, child):
        info, gfile = child._info, child._gfile
        if info.get_file_type() == Gio.FileType.DIRECTORY:
            self.load_dir(gfile.get_path())
        else:
            Gio.AppInfo.launch_default_for_uri(gfile.get_uri(), None)

    def on_select(self, box):
        sel = box.get_selected_children()
        n = len(sel)
        self.selbar.set_reveal_child(n > 0)
        self.sel_label.set_text(f"Zaznaczono: {n}")
        if n >= 1:
            child = sel[-1]
            self._set_preview(child._info, child._gfile)

    def on_search(self, entry):
        q = entry.get_text().lower()
        if not q:
            self._populate(self.entries)
            return
        self._populate([(i, g) for i, g in self.entries if q in i.get_display_name().lower()])

    def on_key(self, w, ev):
        ctrl = ev.state & Gdk.ModifierType.CONTROL_MASK
        if ctrl and ev.keyval in (Gdk.KEY_k, Gdk.KEY_K):
            self.search.grab_focus()
            return True
        if ev.keyval == Gdk.KEY_BackSpace:
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


def main():
    css = Gtk.CssProvider()
    css.load_from_path(os.path.join(HERE, "nova.css"))
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)
    win = NovaWindow()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
