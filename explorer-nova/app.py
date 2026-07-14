#!/usr/bin/env python3
"""Explorer 2.0 — NOVA shell na GTK4 + libadwaita.

Odwzorowuje mockup "Redesign Explorer Thunar UX": karty-kafelki (GtkGridView
z fabryką — realne, wirtualizowane widżety per plik), pigułkowy sidebar z
kartami urządzeń i mapą dysku, panel podglądu, breadcrumbs, Ctrl+K, widok
listy, operacje plikowe przez GIO, etykiety kolorów (metadane gvfs),
miniatury obrazów, akcje terminala. Wersja 2.0.1.
"""
import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, GObject, Pango, GdkPixbuf

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = "2.0.2"
APP_ID = "io.github.quzopl.Explorer"

TINTS = [
    (("inode/directory",), "tint-dir"),
    (("application/pdf",), "tint-pdf"),
    (("application/zip", "application/x-tar", "application/x-compressed",
      "application/gzip", "application/x-7z", "application/x-xz"), "tint-arch"),
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

# etykiety kolorów (jak w 1.x — te same metadane gvfs)
LABELS = [
    ("Czerwony", "#c94f4f"), ("Pomarańczowy", "#cf7f2e"), ("Żółty", "#c9a800"),
    ("Zielony", "#3f9a50"), ("Niebieski", "#3a76c4"), ("Fioletowy", "#8b5fbf"),
    ("Szary", "#7a7d85"),
]
LBL_BG = "metadata::thunar-highlight-color-background"
LBL_FG = "metadata::thunar-highlight-color-foreground"

TERMINALS = [
    ("konsole", ["konsole", "--workdir"]),
    ("xfce4-terminal", ["xfce4-terminal", "--working-directory"]),
    ("gnome-terminal", ["gnome-terminal", "--working-directory"]),
    ("x-terminal-emulator", ["x-terminal-emulator"]),
    ("xterm", ["xterm"]),
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


def find_terminal():
    for name, argv in TERMINALS:
        if GLib.find_program_in_path(name):
            return argv
    return None


class FileItem(GObject.Object):
    __gtype_name__ = "FileItem"

    def __init__(self, info, gfile):
        super().__init__()
        self.info = info
        self.gfile = gfile

    @property
    def is_dir(self):
        return self.info.get_file_type() == Gio.FileType.DIRECTORY

    def label_color(self):
        return self.info.get_attribute_string(LBL_BG)


class NovaWindow(Adw.ApplicationWindow):
    def __init__(self, app, start_path=None):
        super().__init__(application=app)
        self.set_title("Explorer")
        self.set_default_size(1500, 900)
        self.add_css_class("nova-root")
        self.path = start_path if (start_path and os.path.isdir(start_path)) else GLib.get_home_dir()
        self.history = [self.path]
        self.hist_i = 0
        self.store = Gio.ListStore(item_type=FileItem)
        self.all_items = []
        self.monitor = None
        self.clip = []          # lista GFile
        self.clip_cut = False
        self.view_mode = "grid"

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
        self.stack = Gtk.Stack(vexpand=True)
        self.stack.add_named(self._build_grid(), "grid")
        self.stack.add_named(self._build_list(), "list")
        center.append(self.stack)
        self.progress = self._build_progress()
        center.append(self.progress)
        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("nova-status")
        center.append(self.status)
        body.append(center)

        body.append(self._build_preview())

        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self.on_key)
        self.add_controller(key)

        self.load_dir(self.path)

        st = os.environ.get("EXPLORER_SELFTEST")
        if st:
            GLib.timeout_add(400, self._selftest, st)

    def _selftest(self, dest):
        """Autotest operacji (uruchamiany tylko przez EXPLORER_SELFTEST)."""
        try:
            if self.store.get_n_items() == 0:
                return False
            self.selection.select_item(0, True)
            it = self.store.get_item(0)
            self.clip = [it.gfile]; self.clip_cut = False
            GLib.idle_add(lambda: (self.load_dir(dest, push=False), self.act_paste(), False)[-1])
        except Exception as e:
            open("/tmp/explorer-selftest.txt", "w").write("ERR " + str(e))
        return False

    # ——— header ———
    def _build_header(self):
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        h.add_css_class("nova-header")
        badge = Gtk.Label(label="N"); badge.add_css_class("nova-logo-badge")
        h.append(badge)
        logo = Gtk.Label(label="Explorer"); logo.add_css_class("nova-logo")
        h.append(logo)
        for icon, cb in (("go-previous-symbolic", self.go_back),
                         ("go-next-symbolic", self.go_fwd),
                         ("go-up-symbolic", self.go_up),
                         ("go-home-symbolic", lambda *_: self.load_dir(GLib.get_home_dir()))):
            b = Gtk.Button.new_from_icon_name(icon); b.add_css_class("nova-navbtn")
            b.connect("clicked", cb); h.append(b)
        self.crumbs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        self.crumbs.add_css_class("nova-crumbs")
        h.append(self.crumbs)
        h.append(Gtk.Box(hexpand=True))

        sb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sb.add_css_class("nova-search")
        sb.append(Gtk.Image.new_from_icon_name("system-search-symbolic"))
        self.search = Gtk.Entry(); self.search.set_placeholder_text("Szukaj lub wpisz polecenie")
        self.search.set_width_chars(22); self.search.set_has_frame(False)
        self.search.connect("changed", self.on_search)
        sb.append(self.search)
        kbd = Gtk.Label(label="Ctrl K"); kbd.add_css_class("nova-kbd")
        sb.append(kbd); h.append(sb)

        seg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        seg.add_css_class("nova-seg")
        self.seg_grid = Gtk.Button.new_from_icon_name("view-grid-symbolic")
        self.seg_grid.add_css_class("active")
        self.seg_grid.connect("clicked", lambda *_: self.set_view("grid"))
        self.seg_list = Gtk.Button.new_from_icon_name("view-list-symbolic")
        self.seg_list.connect("clicked", lambda *_: self.set_view("list"))
        seg.append(self.seg_grid); seg.append(self.seg_list)
        h.append(seg)

        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_btn.add_css_class("nova-navbtn")
        m = Gio.Menu()
        m.append("Nowy folder", "win.newfolder")
        m.append("Wklej", "win.paste")
        m.append("Otwórz terminal tutaj", "win.terminal")
        m.append("O programie", "win.about")
        menu_btn.set_menu_model(m)
        h.append(menu_btn)

        dots = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        for cls, cb in (("min", lambda *_: self.minimize()),
                        ("max", self._toggle_max), ("close", lambda *_: self.close())):
            d = Gtk.Button(); d.add_css_class("nova-dot"); d.add_css_class(cls)
            d.set_size_request(13, 13); d.connect("clicked", cb); dots.append(d)
        h.append(dots)
        self._install_actions()
        return h

    def _install_actions(self):
        for name, cb in (("newfolder", self.act_new_folder), ("paste", self.act_paste),
                         ("terminal", self.act_terminal_here), ("about", self.act_about),
                         ("copy", lambda *_: self.act_clip(False)),
                         ("cut", lambda *_: self.act_clip(True)),
                         ("trash", self.act_trash), ("rename", self.act_rename)):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)

    def _toggle_max(self, *_):
        self.unmaximize() if self.is_maximized() else self.maximize()

    # ——— sidebar ———
    def _build_sidebar(self):
        sb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sb.add_css_class("nova-sidebar"); sb.set_size_request(240, -1)
        scr = Gtk.ScrolledWindow(vexpand=True)
        scr.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scr.set_child(inner); sb.append(scr)

        inner.append(self._section("MIEJSCA"))
        places = Gtk.ListBox(); places.add_css_class("nova-list")
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
        ai = Gtk.Label(label="AI", valign=Gtk.Align.CENTER); ai.add_css_class("nova-section-ai")
        sec.append(ai); inner.append(sec)
        col = Gtk.ListBox(); col.add_css_class("nova-list")
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
        l = Gtk.Label(label=text, xalign=0); l.add_css_class("nova-section"); return l

    def _nav_row(self, name, icon, path):
        row = Gtk.ListBoxRow(); row.add_css_class("nova-row"); row._path = path
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        img = Gtk.Image.new_from_icon_name(icon); img.add_css_class("nova-row-icon")
        box.append(img); box.append(Gtk.Label(label=name, xalign=0)); row.set_child(box)
        return row

    def _coll_row(self, label, dot, pred):
        row = Gtk.ListBoxRow(); row.add_css_class("nova-row")
        row._pred = pred; row._label = label
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        d = Gtk.DrawingArea(); d.set_size_request(8, 8); d.set_valign(Gtk.Align.CENTER)
        rgba = Gdk.RGBA(); rgba.parse(dot)
        d.set_draw_func(lambda area, cr, w, h, c=rgba:
                        (cr.set_source_rgba(c.red, c.green, c.blue, 1),
                         cr.arc(w/2, h/2, min(w, h)/2, 0, 6.2832), cr.fill()))
        box.append(d); box.append(Gtk.Label(label=label, xalign=0)); row.set_child(box)
        return row

    def _devices(self):
        devs = [("System", "/")]
        for m in Gio.VolumeMonitor.get().get_mounts():
            r = m.get_root()
            if r and r.is_native() and r.get_path():
                devs.append((m.get_name(), r.get_path()))
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
        nm.add_css_class("nova-dev-name"); top.append(nm)
        pc = Gtk.Label(label=f"{pct}%" if pct >= 0 else "—"); pc.add_css_class("nova-dev-pct")
        top.append(pc); card.append(top)
        lb = Gtk.LevelBar.new_for_interval(0, 100); lb.add_css_class("acc")
        lb.set_value(pct if pct >= 0 else 0); card.append(lb)
        if size:
            sub = Gtk.Label(label=f"{human_size(used)} z {human_size(size)}", xalign=0)
            sub.add_css_class("nova-dev-sub"); card.append(sub)
        click = Gtk.GestureClick(); click.connect("released", lambda *_: self.load_dir(path))
        card.add_controller(click)
        return card

    def _disk_map(self):
        segs = [("#5CE1E6", 18), ("#8B7CFF", 34), ("#F472B6", 12), ("#232d45", 36)]
        area = Gtk.DrawingArea(); area.set_size_request(-1, 10)
        area.set_margin_top(4); area.set_margin_start(6); area.set_margin_end(6)

        def draw(a, cr, w, h, segs=segs):
            total = sum(s[1] for s in segs); x = 0.0
            for c, wt in segs:
                sw = w * wt / total
                rgba = Gdk.RGBA(); rgba.parse(c)
                cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 1)
                cr.rectangle(x, 0, sw, h); cr.fill(); x += sw
        area.set_draw_func(draw)
        return area

    # ——— selection bar ———
    def _build_selbar(self):
        rev = Gtk.Revealer(); rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.add_css_class("nova-selbar")
        self.sel_label = Gtk.Label(label="Zaznaczono: 0", xalign=0, hexpand=True)
        box.append(self.sel_label)
        for label, extra, cb in (("Kopiuj", "primary", lambda *_: self.act_clip(False)),
                                 ("Przenieś", None, lambda *_: self.act_clip(True)),
                                 ("Usuń", "danger", self.act_trash)):
            b = Gtk.Button(label=label); b.add_css_class("nova-pillbtn")
            if extra:
                b.add_css_class(extra)
            b.connect("clicked", cb)
            box.append(b)
        rev.set_child(box)
        return rev

    def _build_progress(self):
        rev = Gtk.Revealer()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.add_css_class("nova-selbar")
        self.prog_label = Gtk.Label(xalign=0)
        self.prog_bar = Gtk.ProgressBar(hexpand=True, valign=Gtk.Align.CENTER)
        box.append(self.prog_label); box.append(self.prog_bar)
        rev.set_child(box)
        return rev

    # ——— grid ———
    def _build_grid(self):
        self.selection = Gtk.MultiSelection(model=self.store)
        self.selection.connect("selection-changed", lambda *_: self.on_select())
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._tile_setup)
        factory.connect("bind", self._tile_bind)
        self.grid = Gtk.GridView(model=self.selection, factory=factory)
        self.grid.add_css_class("nova-grid")
        self.grid.set_max_columns(12); self.grid.set_min_columns(2)
        self.grid.connect("activate", self.on_activate_grid)
        rc = Gtk.GestureClick(); rc.set_button(3)
        rc.connect("pressed", self.on_right_click)
        self.grid.add_controller(rc)
        scr = Gtk.ScrolledWindow(vexpand=True); scr.set_child(self.grid)
        return scr

    def _tile_setup(self, factory, item):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.add_css_class("nova-tile"); box.set_size_request(128, -1)
        thumb = Gtk.Overlay()
        bg = Gtk.Box(); bg.add_css_class("nova-thumb")
        img = Gtk.Image(); img.set_pixel_size(46)
        img.set_valign(Gtk.Align.CENTER); img.set_halign(Gtk.Align.CENTER)
        pic = Gtk.Picture(); pic.set_can_shrink(True); pic.set_content_fit(Gtk.ContentFit.COVER)
        pic.set_visible(False)
        dot = Gtk.Box(); dot.add_css_class("nova-labeldot")
        dot.set_size_request(12, 12); dot.set_halign(Gtk.Align.END); dot.set_valign(Gtk.Align.START)
        dot.set_margin_top(6); dot.set_margin_end(6); dot.set_visible(False)
        thumb.set_child(bg); thumb.add_overlay(pic); thumb.add_overlay(img); thumb.add_overlay(dot)
        name = Gtk.Label(xalign=0.5, ellipsize=Pango.EllipsizeMode.MIDDLE)
        name.set_max_width_chars(14); name.add_css_class("nova-tile-name")
        sub = Gtk.Label(); sub.add_css_class("nova-tile-sub")
        box.append(thumb); box.append(name); box.append(sub)
        box._bg, box._img, box._pic, box._dot = bg, img, pic, dot
        box._name, box._sub = name, sub
        item.set_child(box)

    def _tile_bind(self, factory, item):
        it = item.get_item(); box = item.get_child(); info = it.info
        for c in list(box._bg.get_css_classes()):
            if c.startswith("tint-"):
                box._bg.remove_css_class(c)
        box._bg.add_css_class(tint_class(info.get_content_type()))
        # miniatura obrazu jeśli to obraz
        box._pic.set_visible(False); box._img.set_visible(True)
        ctype = info.get_content_type() or ""
        if ctype.startswith("image/"):
            tex = self._thumbnail(it.gfile)
            if tex:
                box._pic.set_paintable(tex); box._pic.set_visible(True); box._img.set_visible(False)
        if box._img.get_visible():
            icon = info.get_icon()
            if icon:
                box._img.set_from_gicon(icon)
        # etykieta koloru
        color = it.label_color()
        if color:
            box._dot.set_visible(True)
            self._paint_dot(box._dot, color)
        else:
            box._dot.set_visible(False)
        box._name.set_text(info.get_display_name())
        box._sub.set_text("" if it.is_dir else human_size(info.get_size()))

    def _paint_dot(self, widget, color):
        css = getattr(widget, "_css", None)
        if css is None:
            css = Gtk.CssProvider()
            widget.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 20)
            widget._css = css
        css.load_from_data((".nova-labeldot{background-color:%s;border-radius:50%%;"
                            "border:2px solid #0C111E;}" % color).encode())

    def _thumbnail(self, gfile):
        try:
            path = gfile.get_path()
            if not path:
                return None
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 120, 90, True)
            return Gdk.Texture.new_for_pixbuf(pb)
        except Exception:
            return None

    # ——— list view ———
    def _build_list(self):
        self.list_sel = Gtk.MultiSelection(model=self.store)
        self.list_sel.connect("selection-changed", lambda *_: self.on_select())
        cv = Gtk.ColumnView(model=self.list_sel)
        cv.add_css_class("nova-columns")

        def col(title, bind, expand=False):
            f = Gtk.SignalListItemFactory()
            f.connect("setup", lambda fa, it: it.set_child(Gtk.Label(xalign=0,
                      ellipsize=Pango.EllipsizeMode.END)))
            f.connect("bind", lambda fa, it: it.get_child().set_text(bind(it.get_item())))
            c = Gtk.ColumnViewColumn(title=title, factory=f)
            c.set_expand(expand)
            return c

        def name_bind(it):
            return it.info.get_display_name()
        # kolumna nazwy z ikoną
        nf = Gtk.SignalListItemFactory()

        def nsetup(fa, it):
            b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            img = Gtk.Image(); lbl = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
            b.append(img); b.append(lbl); b._img, b._lbl = img, lbl
            it.set_child(b)

        def nbind(fa, it):
            b = it.get_child(); info = it.get_item().info
            icon = info.get_icon()
            if icon:
                b._img.set_from_gicon(icon)
            b._lbl.set_text(info.get_display_name())
        nf.connect("setup", nsetup); nf.connect("bind", nbind)
        cn = Gtk.ColumnViewColumn(title="NAZWA", factory=nf); cn.set_expand(True)
        cv.append_column(cn)
        cv.append_column(col("ROZMIAR", lambda it: "" if it.is_dir else human_size(it.info.get_size())))
        cv.append_column(col("TYP", lambda it: it.info.get_content_type() or ""))
        cv.append_column(col("ZMIENIONO", lambda it: (it.info.get_modification_date_time().format("%d.%m.%Y %H:%M")
                                                      if it.info.get_modification_date_time() else "")))
        cv.connect("activate", self.on_activate_list)
        rc = Gtk.GestureClick(); rc.set_button(3)
        rc.connect("pressed", self.on_right_click)
        cv.add_controller(rc)
        self.colview = cv
        scr = Gtk.ScrolledWindow(vexpand=True); scr.set_child(cv)
        return scr

    def set_view(self, mode):
        self.view_mode = mode
        self.stack.set_visible_child_name(mode)
        self.seg_grid.remove_css_class("active"); self.seg_list.remove_css_class("active")
        (self.seg_grid if mode == "grid" else self.seg_list).add_css_class("active")

    def _active_selection(self):
        return self.selection if self.view_mode == "grid" else self.list_sel

    # ——— preview ———
    def _build_preview(self):
        p = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        p.add_css_class("nova-preview"); p.set_size_request(300, -1)
        p.append(self._section("PODGLĄD"))
        self.prev_pic = Gtk.Picture(); self.prev_pic.set_size_request(-1, 150)
        self.prev_pic.set_content_fit(Gtk.ContentFit.CONTAIN); self.prev_pic.set_visible(False)
        p.append(self.prev_pic)
        self.prev_thumb = Gtk.Box(); self.prev_thumb.add_css_class("nova-prev-thumb")
        self.prev_thumb.set_size_request(-1, 150)
        p.append(self.prev_thumb)
        self.prev_title = Gtk.Label(label="Wybierz plik", xalign=0,
                                    ellipsize=Pango.EllipsizeMode.MIDDLE)
        self.prev_title.add_css_class("nova-prev-title"); p.append(self.prev_title)
        self.prev_grid = Gtk.Grid(column_spacing=10, row_spacing=6); p.append(self.prev_grid)
        return p

    def _set_preview(self, it):
        info, gfile = it.info, it.gfile
        child = self.prev_grid.get_first_child()
        while child:
            nxt = child.get_next_sibling(); self.prev_grid.remove(child); child = nxt
        self.prev_title.set_text(info.get_display_name())
        tex = self._thumbnail(gfile) if (info.get_content_type() or "").startswith("image/") else None
        if tex:
            self.prev_pic.set_paintable(tex); self.prev_pic.set_visible(True)
            self.prev_thumb.set_visible(False)
        else:
            self.prev_pic.set_visible(False); self.prev_thumb.set_visible(True)
        rows = [("Rozmiar", human_size(info.get_size()) if not it.is_dir else "folder"),
                ("Typ", info.get_content_type() or "—"),
                ("Ścieżka", gfile.get_path() or "")]
        mt = info.get_modification_date_time()
        if mt:
            rows.insert(1, ("Zmieniono", mt.format("%d.%m.%Y %H:%M")))
        for i, (k, v) in enumerate(rows):
            kl = Gtk.Label(label=k, xalign=0); kl.add_css_class("nova-prev-k")
            vl = Gtk.Label(label=v, xalign=1, hexpand=True, ellipsize=Pango.EllipsizeMode.MIDDLE)
            vl.add_css_class("nova-prev-v")
            self.prev_grid.attach(kl, 0, i, 1, 1); self.prev_grid.attach(vl, 1, i, 1, 1)

    # ——— listing / nav ———
    def load_dir(self, path, push=True):
        self.path = path
        if push:
            self.history = self.history[:self.hist_i + 1] + [path]
            self.hist_i = len(self.history) - 1
        self._render_crumbs()
        try:
            gf = Gio.File.new_for_path(path)
            en = gf.enumerate_children("standard::*,time::modified," + LBL_BG,
                                       Gio.FileQueryInfoFlags.NONE, None)
        except GLib.Error as e:
            self.status.set_text(f"Błąd: {e.message}"); return
        items = []
        info = en.next_file(None)
        while info:
            if not info.get_is_hidden():
                items.append(FileItem(info, gf.get_child(info.get_name())))
            info = en.next_file(None)
        items.sort(key=lambda it: (not it.is_dir, it.info.get_display_name().lower()))
        self.all_items = items
        self._fill(items); self._watch(gf)
        nd = sum(1 for it in items if it.is_dir)
        self.status.set_markup(
            f"{len(items)} elementów · {nd} folderów · {len(items)-nd} plików"
            f"    <span foreground='#34D399'>●</span> Indeks aktualny")

    def _watch(self, gf):
        if self.monitor:
            self.monitor.cancel()
        try:
            self.monitor = gf.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
            self.monitor.connect("changed", self._on_dir_changed)
        except GLib.Error:
            self.monitor = None

    def _on_dir_changed(self, mon, f, other, event):
        if not getattr(self, "_reload_pending", False):
            self._reload_pending = True
            GLib.timeout_add(250, self._do_reload)

    def _do_reload(self):
        self._reload_pending = False
        self.load_dir(self.path, push=False)
        return False

    def load_collection(self, pred, label):
        matches = [it for it in self.all_items if self._safe_pred(pred, it)]
        self._render_crumbs(virtual=label); self._fill(matches)
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
            nxt = child.get_next_sibling(); self.crumbs.remove(child); child = nxt
        home = GLib.get_home_dir(); parts, p = [], self.path
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
                sep = Gtk.Label(label="›"); sep.add_css_class("nova-crumb-sep")
                self.crumbs.append(sep)
            b = Gtk.Button(label=label); b.add_css_class("nova-crumb")
            if i == len(parts) - 1:
                b.add_css_class("active")
            if target:
                b.connect("clicked", lambda _b, t=target: self.load_dir(t))
            self.crumbs.append(b)

    # ——— selection / activation ———
    def _selected_items(self):
        sel = self._active_selection().get_selection()
        return [self.store.get_item(sel.get_nth(i)) for i in range(sel.get_size())]

    def on_activate_grid(self, grid, pos):
        self._open(self.store.get_item(pos))

    def on_activate_list(self, cv, pos):
        self._open(self.store.get_item(pos))

    def _open(self, it):
        if it.is_dir:
            self.load_dir(it.gfile.get_path())
        else:
            Gio.AppInfo.launch_default_for_uri(it.gfile.get_uri(), None)

    def on_select(self):
        items = self._selected_items(); n = len(items)
        self.selbar.set_reveal_child(n > 0)
        self.sel_label.set_text(f"Zaznaczono: {n}")
        if n >= 1:
            self._set_preview(items[-1])

    def on_search(self, entry):
        q = entry.get_text().lower()
        self._fill(self.all_items if not q else
                   [it for it in self.all_items if q in it.info.get_display_name().lower()])

    def on_key(self, ctrl, keyval, keycode, state):
        c = state & Gdk.ModifierType.CONTROL_MASK
        s = state & Gdk.ModifierType.SHIFT_MASK
        if c and keyval in (Gdk.KEY_k, Gdk.KEY_K):
            self.search.grab_focus(); return True
        if self.search.has_focus():
            return False
        if c and keyval in (Gdk.KEY_c, Gdk.KEY_C):
            self.act_clip(False); return True
        if c and keyval in (Gdk.KEY_x, Gdk.KEY_X):
            self.act_clip(True); return True
        if c and keyval in (Gdk.KEY_v, Gdk.KEY_V):
            self.act_paste(); return True
        if keyval == Gdk.KEY_Delete and not s:
            self.act_trash(); return True
        if keyval == Gdk.KEY_Delete and s:
            self.act_delete(); return True
        if keyval == Gdk.KEY_F2:
            self.act_rename(); return True
        if keyval == Gdk.KEY_BackSpace:
            self.go_up(); return True
        return False

    # ——— context menu ———
    def on_right_click(self, gesture, n, x, y):
        items = self._selected_items()
        menu = Gio.Menu()
        if items:
            menu.append("Otwórz", "win.open")
            menu.append("Kopiuj", "win.copy")
            menu.append("Wytnij", "win.cut")
            menu.append("Zmień nazwę", "win.rename")
            menu.append("Przenieś do kosza", "win.trash")
            sub = Gio.Menu()
            for i, (name, _col) in enumerate(LABELS):
                sub.append(name, f"win.label::{i}")
            sub.append("Brak", "win.label::none")
            menu.append_submenu("Etykieta koloru", sub)
            if len(items) == 1 and not items[0].is_dir:
                menu.append("Uruchom w terminalu", "win.runterm")
        else:
            menu.append("Nowy folder", "win.newfolder")
            menu.append("Wklej", "win.paste")
            menu.append("Otwórz terminal tutaj", "win.terminal")
        pop = Gtk.PopoverMenu.new_from_model(menu)
        pop.set_parent(self.stack)
        pop.set_pointing_to(Gdk.Rectangle(x=int(x), y=int(y) + 90, width=1, height=1))
        pop.set_has_arrow(False)
        pop.popup()
        # akcje dynamiczne
        self._ensure_dynamic_actions()

    def _ensure_dynamic_actions(self):
        if getattr(self, "_dyn_done", False):
            return
        self._dyn_done = True
        a_open = Gio.SimpleAction.new("open", None)
        a_open.connect("activate", lambda *_: [self._open(i) for i in self._selected_items()[:1]])
        self.add_action(a_open)
        a_del = Gio.SimpleAction.new("delete", None)
        a_del.connect("activate", self.act_delete); self.add_action(a_del)
        a_run = Gio.SimpleAction.new("runterm", None)
        a_run.connect("activate", self.act_run_terminal); self.add_action(a_run)
        a_lbl = Gio.SimpleAction.new("label", GLib.VariantType.new("s"))
        a_lbl.connect("activate", self.act_label); self.add_action(a_lbl)

    # ——— operacje plikowe ———
    def act_clip(self, cut):
        items = self._selected_items()
        if not items:
            return
        self.clip = [it.gfile for it in items]
        self.clip_cut = cut
        self.status.set_text(("Wycięto " if cut else "Skopiowano ") +
                             f"{len(items)} elementów — wklej w docelowym folderze (Ctrl+V)")

    def act_paste(self, *_):
        if not self.clip or getattr(self, "_op_running", False):
            return
        import threading
        dest_dir = Gio.File.new_for_path(self.path)
        queue = list(self.clip)
        cut = self.clip_cut
        if cut:
            self.clip = []
        self._op_running = True
        self._op_overwrite_all = False
        self.progress.set_reveal_child(True)
        threading.Thread(target=self._paste_worker, args=(queue, cut, dest_dir),
                         daemon=True).start()

    def _paste_worker(self, queue, cut, dest_dir):
        total = len(queue)
        for i, src in enumerate(queue, 1):
            dest = dest_dir.get_child(src.get_basename())
            name = src.get_basename()
            GLib.idle_add(self._prog_update, i, total, cut, name, 0.0)

            def prog(cur, tot, *u, _i=i, _t=total, _n=name):
                if tot:
                    GLib.idle_add(self._prog_update, _i, _t, cut, _n, cur / tot)

            flags = Gio.FileCopyFlags.OVERWRITE if self._op_overwrite_all else Gio.FileCopyFlags.NONE
            try:
                if cut:
                    src.move(dest, flags, None, prog)
                else:
                    src.copy(dest, flags, None, prog)
            except GLib.Error as e:
                if e.matches(Gio.io_error_quark(), Gio.IOErrorEnum.EXISTS):
                    ans = self._ask_overwrite_sync(name)
                    if ans in ("over", "all"):
                        if ans == "all":
                            self._op_overwrite_all = True
                        try:
                            (src.move if cut else src.copy)(dest, Gio.FileCopyFlags.OVERWRITE, None, prog)
                        except GLib.Error as e2:
                            GLib.idle_add(self._error, e2.message)
                    # "skip" -> pomiń
                else:
                    GLib.idle_add(self._error, e.message)
        GLib.idle_add(self._paste_done)

    def _prog_update(self, i, total, cut, name, frac):
        self.prog_label.set_text(f"{'Przenoszenie' if cut else 'Kopiowanie'} {name} ({i}/{total})")
        self.prog_bar.set_fraction(frac)
        return False

    def _paste_done(self):
        self._op_running = False
        self.progress.set_reveal_child(False)
        self.load_dir(self.path, push=False)
        return False

    def _ask_overwrite_sync(self, name):
        """Pyta o nadpisanie z wątku roboczego (blokuje wątek, nie UI)."""
        import threading
        ev = threading.Event()
        box = {"ans": "skip"}

        def ask():
            d = Adw.MessageDialog.new(self, "Plik już istnieje",
                                      f"„{name}” już istnieje w tym folderze.")
            d.add_response("skip", "Pomiń")
            d.add_response("over", "Nadpisz")
            d.add_response("all", "Nadpisz wszystkie")
            d.set_response_appearance("over", Adw.ResponseAppearance.DESTRUCTIVE)
            d.set_response_appearance("all", Adw.ResponseAppearance.DESTRUCTIVE)

            def resp(dlg, r):
                box["ans"] = r
                ev.set()
            d.connect("response", resp)
            d.present()
            return False
        GLib.idle_add(ask)
        ev.wait()
        return box["ans"]

    def act_trash(self, *_):
        items = self._selected_items()
        if not items:
            return
        for it in items:
            try:
                it.gfile.trash(None)
            except GLib.Error as e:
                self._error(f"Kosz: {e.message}")
        self.status.set_text(f"Przeniesiono do kosza: {len(items)}")

    def act_delete(self, *_):
        items = self._selected_items()
        if not items:
            return
        d = Adw.MessageDialog.new(self, "Usunąć trwale?",
                                  f"{len(items)} elementów zostanie usuniętych bezpowrotnie.")
        d.add_response("cancel", "Anuluj"); d.add_response("del", "Usuń trwale")
        d.set_response_appearance("del", Adw.ResponseAppearance.DESTRUCTIVE)

        def resp(dlg, r):
            if r == "del":
                for it in items:
                    try:
                        it.gfile.delete(None)
                    except GLib.Error as e:
                        self._error(e.message)
        d.connect("response", resp); d.present()

    def act_rename(self, *_):
        items = self._selected_items()
        if len(items) != 1:
            return
        it = items[0]
        d = Adw.MessageDialog.new(self, "Zmień nazwę", None)
        entry = Gtk.Entry(text=it.info.get_display_name())
        entry.set_margin_top(6); entry.set_margin_start(12); entry.set_margin_end(12)
        d.set_extra_child(entry)
        d.add_response("cancel", "Anuluj"); d.add_response("ok", "Zmień nazwę")
        d.set_default_response("ok")

        def resp(dlg, r):
            if r == "ok":
                new = entry.get_text().strip()
                if new and new != it.info.get_display_name():
                    try:
                        it.gfile.set_display_name(new, None)
                    except GLib.Error as e:
                        self._error(e.message)
        d.connect("response", resp); d.present()

    def act_new_folder(self, *_):
        d = Adw.MessageDialog.new(self, "Nowy folder", None)
        entry = Gtk.Entry(text="Nowy folder")
        entry.set_margin_top(6); entry.set_margin_start(12); entry.set_margin_end(12)
        d.set_extra_child(entry)
        d.add_response("cancel", "Anuluj"); d.add_response("ok", "Utwórz")
        d.set_default_response("ok")

        def resp(dlg, r):
            if r == "ok":
                name = entry.get_text().strip()
                if name:
                    try:
                        Gio.File.new_for_path(os.path.join(self.path, name)).make_directory(None)
                    except GLib.Error as e:
                        self._error(e.message)
        d.connect("response", resp); d.present()

    def act_label(self, action, param):
        val = param.get_string()
        for it in self._selected_items():
            try:
                if val == "none":
                    it.gfile.set_attribute(LBL_BG, Gio.FileAttributeType.INVALID, None,
                                           Gio.FileQueryInfoFlags.NONE, None)
                    it.gfile.set_attribute(LBL_FG, Gio.FileAttributeType.INVALID, None,
                                           Gio.FileQueryInfoFlags.NONE, None)
                else:
                    _, color = LABELS[int(val)]
                    it.gfile.set_attribute_string(LBL_BG, color, Gio.FileQueryInfoFlags.NONE, None)
                    it.gfile.set_attribute_string(LBL_FG, "#ffffff", Gio.FileQueryInfoFlags.NONE, None)
            except GLib.Error as e:
                self._error(e.message)
        self.load_dir(self.path, push=False)

    def act_terminal_here(self, *_):
        argv = find_terminal()
        if not argv:
            self._error("Brak zainstalowanego terminala"); return
        if len(argv) > 1:
            cmd = argv + [self.path]
        else:
            cmd = argv
        try:
            Gio.Subprocess.new(cmd, Gio.SubprocessFlags.NONE)
        except GLib.Error as e:
            self._error(e.message)

    def act_run_terminal(self, *_):
        items = self._selected_items()
        if len(items) != 1:
            return
        f = items[0].gfile.get_path()
        if not f:
            return
        argv = find_terminal()
        if not argv:
            self._error("Brak terminala"); return
        # nazwa pliku jako argument pozycyjny ($1), NIE wklejana w skrypt —
        # inaczej plik nazwany np. '; rm -rf ~' wykonałby dowolny kod
        run = ('f="$1"; cd "$(dirname "$f")" || exit 1; '
               'if [ -x "$f" ]; then "$f"; else sh "$f"; fi; '
               'echo; echo "[koniec — Enter zamyka]"; read _')
        base = argv[0]
        if base == "konsole":
            cmd = ["konsole", "-e", "sh", "-c", run, "explorer", f]
        elif base == "xfce4-terminal":
            cmd = ["xfce4-terminal", "-x", "sh", "-c", run, "explorer", f]
        elif base == "gnome-terminal":
            cmd = ["gnome-terminal", "--", "sh", "-c", run, "explorer", f]
        else:
            cmd = [base, "-e", "sh", "-c", run, "explorer", f]
        try:
            Gio.Subprocess.new(cmd, Gio.SubprocessFlags.NONE)
        except GLib.Error as e:
            self._error(e.message)

    def act_about(self, *_):
        about = Adw.AboutWindow(transient_for=self, application_name="Explorer",
                                application_icon="system-file-manager",
                                version=VERSION,
                                developer_name="quzopl",
                                comments="Menedżer plików w stylu NOVA (GTK4 + libadwaita).",
                                website="https://github.com/quzopl/explorer-thunar",
                                license_type=Gtk.License.GPL_2_0)
        about.present()

    def _error(self, msg):
        d = Adw.MessageDialog.new(self, "Błąd", msg)
        d.add_response("ok", "OK"); d.present()

    def go_up(self, *_):
        parent = os.path.dirname(self.path.rstrip("/")) or "/"
        if parent != self.path:
            self.load_dir(parent)

    def go_back(self, *_):
        if self.hist_i > 0:
            self.hist_i -= 1; self.load_dir(self.history[self.hist_i], push=False)

    def go_fwd(self, *_):
        if self.hist_i < len(self.history) - 1:
            self.hist_i += 1; self.load_dir(self.history[self.hist_i], push=False)


class NovaApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.start_path = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        css = Gtk.CssProvider()
        css.load_from_path(os.path.join(HERE, "style.css"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)

    def do_command_line(self, cmdline):
        args = cmdline.get_arguments()
        if len(args) > 1 and os.path.isdir(args[1]):
            self.start_path = args[1]
        self.activate()
        return 0

    def do_activate(self):
        NovaWindow(self, self.start_path).present()


if __name__ == "__main__":
    import sys
    NovaApp().run(sys.argv)
