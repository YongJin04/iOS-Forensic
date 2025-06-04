from tkinter import ttk, messagebox
import tkinter as tk
import sqlite3
from pathlib import Path
from datetime import datetime
import unicodedata
from importlib import import_module

from gui.components.document_ui.document_utils import render_preview


def fetch_iCloud_items(backup_path: str):
    db_path = Path(backup_path) / "ad" / "ad93b887b94d8d6c485aed7c0cb561474e5f10c1"
    if not db_path.exists():
        return [("Error", f"DB not found: {db_path}", "")]

    rows = []
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT item_filename, version_size, item_birthtime
                  FROM server_items
                 WHERE item_type = 1
                 ORDER BY item_birthtime DESC
            """)
            for fname, fsize, birth in cur.fetchall():
                fname = unicodedata.normalize("NFC", fname or "")
                ts = int(birth or 0)
                created = (
                    datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                    if ts else "Unknown"
                )
                rows.append((fname, fsize or 0, created))
    except Exception as e:
        rows.append(("Error", str(e), ""))
    return rows


def _find_backup_file(dest_root: Path, filename: str, expected_size: int | None = None) -> Path | None:
    if not dest_root.exists():
        return None
    for p in dest_root.rglob('*'):
        if p.is_file() and p.name == filename:
            if expected_size is None or p.stat().st_size == expected_size:
                return p
    return None



def display_iCloud(content_frame, backup_path: str):
    for w in content_frame.winfo_children():
        w.destroy()

    pw = ttk.PanedWindow(content_frame, orient="horizontal")
    pw.pack(fill="both", expand=True)

    left = ttk.Frame(pw)
    right = ttk.Frame(pw)
    pw.add(left,  weight=4)
    pw.add(right, weight=6)

    header = ttk.Frame(left)
    header.pack(anchor="w", pady=(0, 6), fill="x")
    ttk.Label(header, text="☁️  iCloud Files", style="CardHeader.TLabel").pack(side="left")

    def link_icloud():
        try:
            icloud_utiles = import_module("artifact_analyzer.iCloud.iCloud_utiles")
        except ModuleNotFoundError:
            try:
                icloud_utiles = import_module("iCloud_utiles")
            except ModuleNotFoundError:
                tk.messagebox.showerror("Import Error", "iCloud_utiles module not found.")
                return

        def refresh_after_download():
            nonlocal data
            data = fetch_iCloud_items(backup_path)
            populate()
            update_status_label()

        dest_root = Path(backup_path) / "iCloud_Drive_Backup"
        icloud_utiles.gui_download(
            parent=content_frame.winfo_toplevel(),
            dest_root=dest_root,
            on_complete=refresh_after_download,
        )

    ttk.Button(header, text="Sync iCloud", command=link_icloud).pack(side="left", padx=(10, 0))

    table = ttk.Frame(left)
    table.pack(fill="both", expand=True)

    cols = ("filename", "size", "created")
    tree = ttk.Treeview(table, columns=cols, show="headings")
    tree.heading("filename", text="FileName")
    tree.heading("size",     text="FileSize")
    tree.heading("created",  text="Created Time")
    tree.column("filename", width=250, stretch=True)
    tree.column("size",     width=50, anchor="e")
    tree.column("created",  width=100, anchor="center")
    tree.tag_configure("stripe", background="#f5f5f5")

    vsb = ttk.Scrollbar(table, orient="vertical",   command=tree.yview)
    hsb = ttk.Scrollbar(table, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    table.rowconfigure(0, weight=1)
    table.columnconfigure(0, weight=1)

    data = fetch_iCloud_items(backup_path)

    def populate():
        tree.delete(*tree.get_children())
        for i, row in enumerate(data):
            tag = ("stripe",) if i % 2 else ()
            tree.insert("", "end", values=row, tags=tag)

    populate()

    status_lbl = ttk.Label(right, justify="center")
    status_lbl.pack(expand=True)

    def update_status_label():
        dest_root = Path(backup_path) / "iCloud_Drive_Backup"
        if dest_root.exists():
            status_lbl.config(text="✅  iCloud Synced.\nPreview available.")
        else:
            status_lbl.config(text="⚠️  iCloud Sync Needed.\nPreview unavailable.")

    update_status_label()

    def _preview_selected(_e=None):
        sel = tree.selection()
        if not sel:
            return
        values = tree.item(sel[0]).get('values', [None, 0])
        fname = values[0]
        fsize = values[1]
        if not fname or fname.startswith("Error"):
            return

        dest_root = Path(backup_path) / "iCloud_Drive_Backup"
        file_path = _find_backup_file(dest_root, fname, expected_size=fsize)

        for w in right.winfo_children():
            w.destroy()

        if not file_path:
            ttk.Label(right, text=f"❌  File '{fname}' not found or size mismatch.").pack(expand=True)
            return

        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        preview_frame = ttk.Frame(right)
        preview_frame.grid(row=0, column=0, sticky="nsew")

        preview_canvas = tk.Canvas(preview_frame, highlightthickness=0, bg="white")
        preview_canvas.grid(row=0, column=0, sticky="nsew")

        v_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=preview_canvas.yview)
        preview_canvas.configure(yscrollcommand=v_scroll.set)
        v_scroll.grid(row=0, column=1, sticky="ns")

        h_scroll = ttk.Scrollbar(preview_frame, orient="horizontal", command=preview_canvas.xview)
        preview_canvas.configure(xscrollcommand=h_scroll.set)
        h_scroll.grid(row=1, column=0, sticky="ew")

        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        inner_frame = ttk.Frame(preview_canvas)
        window_id = preview_canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        def _on_frame_configure(event):
            preview_canvas.configure(scrollregion=preview_canvas.bbox("all"))
        inner_frame.bind("<Configure>", _on_frame_configure)

        def _on_canvas_configure(event):
            new_w = event.width
            new_h = event.height
            preview_canvas.itemconfig(window_id, width=new_w, height=new_h)
        preview_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_preview_enter(e):
            preview_canvas.focus_set()

        def _on_preview_wheel(e):
            preview_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        preview_canvas.bind("<Enter>", _on_preview_enter)
        preview_canvas.bind("<MouseWheel>", _on_preview_wheel)

        render_preview(inner_frame, file_path)

        def _on_tree_enter(e):
            tree.focus_set()

        def _on_tree_wheel(e):
            tree.yview_scroll(int(-1 * (e.delta / 120)), "units")

        tree.bind("<Enter>", _on_tree_enter)
        tree.bind("<MouseWheel>", _on_tree_wheel)

    tree.bind("<<TreeviewSelect>>", _preview_selected)
    tree.bind("<Enter>", lambda e: tree.focus_set())
    left.bind("<Enter>", lambda e: None)
