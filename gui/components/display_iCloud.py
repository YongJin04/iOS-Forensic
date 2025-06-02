from tkinter import ttk, messagebox
import tkinter as tk
import sqlite3
from pathlib import Path
from datetime import datetime
import unicodedata
from importlib import import_module
import os
import platform
import subprocess

# ────────────────────────────────────────────────────────────
# 선택적 외부 라이브러리 – 없으면 축소 동작
# ────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageTk  # 이미지 미리보기
except ImportError:  # 최소 동작 보장
    Image = ImageTk = None

try:
    from pdf2image import convert_from_path  # PDF 1page → 이미지
except ImportError:
    convert_from_path = None

# ────────────────────────────────────────────────────────────
# DB → Python
# ────────────────────────────────────────────────────────────

def fetch_iCloud_items(backup_path: str):
    db_path = (
        Path(backup_path)
        / "ad"
        / "ad93b887b94d8d6c485aed7c0cb561474e5f10c1"
    )
    if not db_path.exists():
        return [("Error", f"DB not found: {db_path}", "")]

    rows: list[tuple[str, int, str]] = []
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT item_filename, version_size, item_birthtime
                  FROM server_items
                 WHERE item_type = 1
                 ORDER BY item_birthtime DESC
                """
            )
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


# ────────────────────────────────────────────────────────────
# Helper – 백업 경로 검색 & 외부 열기
# ────────────────────────────────────────────────────────────

def _find_backup_file(dest_root: Path, filename: str) -> Path | None:
    """dest_root 이하에서 filename과 정확히 일치하는 첫 파일 반환"""
    if not dest_root.exists():
        return None
    for p in dest_root.rglob('*'):
        if p.is_file() and p.name == filename:
            return p
    return None


def _open_external(filepath: Path):
    """OS 기본 앱으로 열기"""
    try:
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":
            subprocess.call(["open", str(filepath)])
        else:
            subprocess.call(["xdg-open", str(filepath)])
    except Exception as e:
        messagebox.showerror("Open Error", str(e))


# ────────────────────────────────────────────────────────────
# UI
# ────────────────────────────────────────────────────────────

def display_iCloud(content_frame, backup_path: str):
    # ── 0. 초기화
    for w in content_frame.winfo_children():
        w.destroy()

    # ── 1. 좌·우 패널
    left  = ttk.Frame(content_frame)
    right = ttk.Frame(content_frame, width=360)
    left.pack(side="left", fill="both", expand=True)
    right.pack(side="left", fill="both")
    right.pack_propagate(False)

    # ── 2. 헤더 + 버튼
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
                tk.messagebox.showerror("Import Error", "iCloud_utiles 모듈을 찾을 수 없습니다.")
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

    ttk.Button(header, text="iCloud 연동", command=link_icloud).pack(side="left", padx=(10, 0))

    # ── 3. Treeview
    table = ttk.Frame(left)
    table.pack(fill="both", expand=True)

    cols  = ("filename", "size", "created")
    tree  = ttk.Treeview(table, columns=cols, show="headings")
    tree.heading("filename", text="FileName")
    tree.heading("size",     text="FileSize")
    tree.heading("created",  text="FileCreateTime")
    tree.column("filename", width=320, stretch=True)
    tree.column("size",     width=100, anchor="e")
    tree.column("created",  width=150, anchor="center")
    tree.tag_configure("stripe", background="#f5f5f5")

    vsb = ttk.Scrollbar(table, orient="vertical",   command=tree.yview)
    hsb = ttk.Scrollbar(table, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    table.rowconfigure(0, weight=1)
    table.columnconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    # ── 4. 데이터
    data = fetch_iCloud_items(backup_path)

    def populate():
        tree.delete(*tree.get_children())
        for i, row in enumerate(data):
            tag = ("stripe",) if i % 2 else ()
            tree.insert("", "end", values=row, tags=tag)

    populate()

    # ── 5. 상태 라벨
    status_lbl = ttk.Label(right, justify="center")
    status_lbl.pack(expand=True)

    def update_status_label():
        dest_root = Path(backup_path) / "iCloud_Drive_Backup"
        if dest_root.exists():
            status_lbl.config(text="✅  iCloud 연동됨.\n미리보기 가능")
        else:
            status_lbl.config(text="⚠️  iCloud 연동 필요.\n미리보기 불가능")

    update_status_label()

    # ── 6. 선택 이벤트 – 파일 미리보기
    def _preview_selected(_e=None):
        sel = tree.selection()
        if not sel:
            return
        fname = tree.item(sel[0]).get('values', [None])[0]
        if not fname or fname.startswith("Error"):
            return

        dest_root = Path(backup_path) / "iCloud_Drive_Backup"
        file_path = _find_backup_file(dest_root, fname)

        # 우측 패널 클리어
        for w in right.winfo_children():
            w.destroy()

        if not file_path:
            ttk.Label(right, text=f"❌  '{fname}' 파일을 찾을 수 없습니다.").pack(expand=True)
            return

        ext = file_path.suffix.lower()

        # 이미지 → 직접 표시
        if ext in {'.png', '.jpg', '.jpeg', '.gif'} and Image and ImageTk:
            try:
                img = Image.open(file_path)
                img.thumbnail((340, 340))
                photo = ImageTk.PhotoImage(img)
                lbl = ttk.Label(right, image=photo)
                lbl.image = photo  # GC 방지
                lbl.pack(expand=True)
            except Exception as e:
                ttk.Label(right, text=f"⚠️ 이미지 로드 오류: {e}").pack(expand=True)

        # PDF → 첫 페이지 이미지 변환 (pdf2image 필요)
        elif ext == '.pdf' and convert_from_path and ImageTk:
            try:
                pages = convert_from_path(str(file_path), first_page=1, last_page=1, size=(340, None))
                if pages:
                    pages[0].thumbnail((340, 340))
                    photo = ImageTk.PhotoImage(pages[0])
                    lbl = ttk.Label(right, image=photo)
                    lbl.image = photo
                    lbl.pack(expand=True)
            except Exception as e:
                ttk.Label(right, text=f"⚠️ PDF 미리보기 실패: {e}").pack(expand=True)

        # mp4 / pptx / docx 등 → 외부 앱으로 열기 버튼
        elif ext in {'.mp4', '.pptx', '.docx', '.pdf'}:
            ttk.Label(right, text=f"📄  {file_path.name}").pack(pady=(60, 10))
            ttk.Button(
                right,
                text="외부 앱으로 열기",
                command=lambda p=file_path: _open_external(p)
            ).pack()
        else:
            ttk.Label(right, text="⚠️ 지원되지 않는 형식입니다.").pack(expand=True)

    tree.bind("<<TreeviewSelect>>", _preview_selected)
    tree.bind("<MouseWheel>", lambda e: tree.yview_scroll(int(-1 * (e.delta / 120)), "units"))
