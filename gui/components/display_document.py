import sqlite3
import plistlib
import unicodedata
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from gui.components.document_ui.document_utils import render_preview

LEADS = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
VOWELS = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
TAILS = ['', 'ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']

def compose_jamo(text: str) -> str:
    result = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in LEADS and i + 1 < len(text) and text[i + 1] in VOWELS:
            L = LEADS.index(ch)
            V = VOWELS.index(text[i + 1])
            T = 0
            consumed = 2
            if i + 2 < len(text) and text[i + 2] in TAILS and TAILS.index(text[i + 2]) != 0:
                T = TAILS.index(text[i + 2])
                consumed = 3
            code = 0xAC00 + (L * 21 + V) * 28 + T
            result.append(chr(code))
            i += consumed
        else:
            result.append(ch)
            i += 1
    return ''.join(result)

def fetch_files(backup_path: str):
    db_path = Path(backup_path) / "Manifest.db"
    if not db_path.exists():
        return [("ERROR", f"DB not found: {db_path}", "", b"")]

    rows = []
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT relativePath, domain, fileID, file
                FROM Files
                WHERE LOWER(relativePath) LIKE '%.pdf'
                   OR LOWER(relativePath) LIKE '%.xlsx'
                   OR LOWER(relativePath) LIKE '%.pptx'
                   OR LOWER(relativePath) LIKE '%.docx'
                   OR LOWER(relativePath) LIKE '%.csv'
                   OR LOWER(relativePath) LIKE '%.txt'
            """)
            rows = cur.fetchall()
    except Exception as e:
        rows.append(("ERROR", str(e), "", b""))
    return rows

def display_document(content_frame, backup_path: str):
    for w in content_frame.winfo_children():
        w.destroy()

    pw = ttk.PanedWindow(content_frame, orient="horizontal")
    pw.pack(fill="both", expand=True)
    left = ttk.Frame(pw)
    right = ttk.Frame(pw)
    pw.add(left, weight=4)
    pw.add(right, weight=6)

    header = ttk.Frame(left)
    header.pack(anchor="w", pady=(0, 6), fill="x")
    ttk.Label(header, text="📄  Documents (pdf, xlsx, docx, pptx, csv, txt)", style="CardHeader.TLabel").pack(side="left")

    table_frame = ttk.Frame(left)
    table_frame.pack(fill="both", expand=True)

    cols = ("filename", "filepath", "filesize", "createtime")
    tree = ttk.Treeview(table_frame, columns=cols, show="headings")
    for col, label, anchor in zip(cols, ["FileName", "FilePath", "FileSize", "CreateTime"], ["w", "w", "e", "center"]):
        tree.heading(col, text=label)
        tree.column(col, anchor=anchor)
    tree.column("filename", width=450, stretch=True)
    tree.column("filepath", width=50, stretch=True)
    tree.column("filesize", width=60)
    tree.column("createtime", width=130)

    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    raw_data = fetch_files(backup_path)
    parsed = []
    for rel_path, domain, file_id, file_blob in raw_data:
        birth_ts = 0
        birth_str = ""
        if rel_path != "ERROR":
            try:
                info = plistlib.loads(file_blob)
                objects = info.get("$objects", [])
                if isinstance(objects, list) and len(objects) > 1:
                    entry = objects[1]
                    bval = entry.get("Birth", None)
                    if bval is not None:
                        birth_ts = int(bval)
                        birth_str = datetime.utcfromtimestamp(birth_ts).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                birth_ts = 0
        parsed.append((rel_path, domain, file_id, file_blob, birth_ts, birth_str))

    parsed.sort(key=lambda x: x[4], reverse=True)

    item_to_fileid = {}

    def populate():
        tree.delete(*tree.get_children())
        item_to_fileid.clear()
        for i, (rel_path, domain, file_id, file_blob, birth_ts, birth_str) in enumerate(parsed):
            tag = ("stripe",) if i % 2 else ()
            if rel_path == "ERROR":
                tree.insert("", "end", values=(domain, "", "", ""), tags=tag)
                continue

            raw_filename = Path(rel_path).name
            filename = compose_jamo(unicodedata.normalize("NFC", raw_filename))
            combined = f"{domain}/{rel_path}" if domain else rel_path
            filepath = compose_jamo(unicodedata.normalize("NFC", combined))

            filesize = ""
            try:
                info = plistlib.loads(file_blob)
                objects = info.get("$objects", [])
                if isinstance(objects, list) and len(objects) > 1:
                    entry = objects[1]
                    size_val = entry.get("Size", None)
                    filesize = str(size_val) if size_val is not None else ""
            except Exception:
                filesize = ""

            item = tree.insert("", "end", values=(filename, filepath, filesize, birth_str), tags=tag)
            item_to_fileid[item] = file_id

    populate()

    status_lbl = ttk.Label(right, justify="center", text="ℹ️  파일을 선택하면 여기에 미리보기가 표시됩니다.")
    status_lbl.pack(expand=True)

    def _preview_selected(_e=None):
        sel = tree.selection()
        if not sel:
            return
        item = sel[0]
        file_id = item_to_fileid.get(item, "")
        if not file_id:
            return

        subdir = file_id[:2]
        file_path = Path(backup_path) / subdir / file_id

        for w in right.winfo_children():
            w.destroy()

        if not file_path.exists():
            ttk.Label(right, text=f"❌  File not found:\n{file_path}").pack(expand=True)
            return

        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        preview_frame = ttk.Frame(right)
        preview_frame.grid(row=0, column=0, sticky="nsew")
        def get_relative_path(backup_path, file_path):
            import os
            db_path = os.path.join(backup_path, 'Manifest.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT relativePath FROM Files WHERE fileID = ?", (file_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            return Path(result[0]).suffix.lower()

        ext = get_relative_path(backup_path, file_path)
        render_preview(preview_frame, file_path, ext)

    tree.tag_configure("stripe", background="#f5f5f5")
    tree.bind("<<TreeviewSelect>>", _preview_selected)
    tree.bind("<Enter>", lambda e: tree.focus_set())
