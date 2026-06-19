# Etap 3 — Funkcje (plan implementacji)

> REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** Zawsze widoczne pole wyszukiwania w pasku (jak Windows), na natywnym silniku Thunara.

**Architecture:** Jeden patch w `thunar/thunar-window.c`: callback `thunar_window_explorer_searchbox_activate` + wstawienie `GtkSearchEntry` w `thunar_window_location_toolbar_create`. Reuse `thunar_window_start_open_location` / `thunar_window_action_cancel_search`.

## Global Constraints
- Bazuje na Etapach 1-2; build `scripts/build.sh` + `scripts/install-branding.sh`.
- Zmiana jako `patches/07-search-box.patch`; nie dotykać systemowego Thunara.

---

### Task 1: Callback aktywacji pola wyszukiwania

**Files:** Modify `thunar-src/thunar/thunar-window.c`; Create `patches/07-search-box.patch`.

- [ ] **Step 1: Backup** — `cp thunar-src/thunar/thunar-window.c thunar-src/thunar/thunar-window.c.t3`
- [ ] **Step 2: Dodaj callback** tuż przed `thunar_window_location_toolbar_create` (definicją z `{`):

```c
static void
thunar_window_explorer_searchbox_activate (GtkSearchEntry *entry,
                                           ThunarWindow   *window)
{
  const gchar *text;
  gchar       *query;

  _thunar_return_if_fail (THUNAR_IS_WINDOW (window));

  text = gtk_entry_get_text (GTK_ENTRY (entry));
  if (text == NULL || *text == '\0')
    {
      thunar_window_action_cancel_search (window);
      return;
    }

  query = g_strconcat (thunar_util_get_search_prefix (), text, NULL);
  thunar_window_start_open_location (window, query);
  g_free (query);
}
```

### Task 2: Wstaw pole do paska

- [ ] **Step 3: W `thunar_window_location_toolbar_create`**, po linii tworzącej `window->location_toolbar_item_search = ...`, dodaj:

```c
  /* Explorer: zawsze widoczne pole wyszukiwania (jak Windows) */
  {
    GtkToolItem *explorer_search_item = gtk_tool_item_new ();
    GtkWidget   *explorer_searchbox = gtk_search_entry_new ();
    gtk_entry_set_placeholder_text (GTK_ENTRY (explorer_searchbox), _("Szukaj"));
    gtk_widget_set_size_request (explorer_searchbox, 220, -1);
    gtk_widget_set_valign (explorer_searchbox, GTK_ALIGN_CENTER);
    gtk_container_add (GTK_CONTAINER (explorer_search_item), explorer_searchbox);
    g_signal_connect (G_OBJECT (explorer_searchbox), "activate",
                      G_CALLBACK (thunar_window_explorer_searchbox_activate), window);
    g_object_set_data_full (G_OBJECT (explorer_search_item), "id", g_strdup ("explorer-search"), g_free);
    g_object_set_data_full (G_OBJECT (explorer_search_item), "label", g_strdup (_("Search Box")), g_free);
    g_object_set_data_full (G_OBJECT (explorer_search_item), "icon", g_strdup ("system-search"), g_free);
    thunar_g_object_set_guint_data (G_OBJECT (explorer_search_item), "default-order", item_order++);
    gtk_toolbar_insert (GTK_TOOLBAR (window->location_toolbar), explorer_search_item, -1);
  }
```

- [ ] **Step 4: Build** — `bash scripts/build.sh && bash scripts/install-branding.sh` → bez błędów kompilacji.

### Task 3: Weryfikacja

- [ ] **Step 5: Start + zrzut** — uruchom `./install/bin/explorer "$HOME"`, zrzut spectacle; potwierdź pole „Szukaj" widoczne w pasku.
- [ ] **Step 6: Test funkcjonalny** — wpisz frazę w polu (lub przez `xdotool`/ręcznie) i Enter; wyniki rekurencyjne. (Min.: brak błędów krytycznych przy starcie.)
- [ ] **Step 7: Patch + commit**
```bash
diff -u thunar-src/thunar/thunar-window.c.t3 thunar-src/thunar/thunar-window.c | sed 's|thunar-src/||g' > patches/07-search-box.patch
git add patches/07-search-box.patch
git commit -m "feat: patch — zawsze widoczne pole wyszukiwania w pasku (jak Windows)"
```

## Self-Review
- Pole wyszukiwania → Task 1-2 ✓; weryfikacja → Task 3 ✓.
- Funkcje nazwane spójnie; reuse `thunar_window_start_open_location` / `_cancel_search` (istnieją). `thunar_util_get_search_prefix` dostępne (już używane w tym pliku).
