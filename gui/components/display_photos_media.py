from __future__ import annotations

import io
import os
import sqlite3
import subprocess
import tempfile
import threading
import concurrent.futures
from pathlib import Path
from typing import List, Tuple, Dict, Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import rawpy
import imageio_ffmpeg
from PIL import Image, ImageTk

os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ModuleNotFoundError:
    pass

COLS, ROWS = 9, 4
PAGE_SIZE = COLS * ROWS
THUMB_SIDE = 120

IMG_EXTS = {".png", ".jpg", ".jpeg", ".heic", ".dng"}
VID_EXTS = {".mov", ".mp4"}

# ─────────────────────────────────────────────────────────────
# Deleted-flag 판정 (MBFile ▸ ExtendedAttributes)
# ─────────────────────────────────────────────────────────────
import plistlib


def _get_uid(obj):
    return obj.data if isinstance(obj, plistlib.UID) else obj


def _trashed_val_true(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, (bytes, bytearray, memoryview)):
        return len(val) > 0 and val[0] == 1
    return False


def _is_trashed_blob(blob: bytes) -> bool:
    try:
        outer = plistlib.loads(blob)
    except Exception:
        return False
    objs = outer.get("$objects")
    if not objs:
        return False
    root_uid = _get_uid(outer["$top"]["root"])
    if not isinstance(root_uid, int) or root_uid >= len(objs):
        return False
    root = objs[root_uid]
    ext_attr = root.get("ExtendedAttributes")
    if ext_attr is None:
        return False
    ext_uid = _get_uid(ext_attr)
    if not isinstance(ext_uid, int) or ext_uid >= len(objs):
        return False
    ext_blob = objs[ext_uid]
    if not isinstance(ext_blob, (bytes, bytearray)):
        return False
    try:
        attrs = plistlib.loads(ext_blob)
    except Exception:
        return False
    return _trashed_val_true(attrs.get("com.apple.assetsd.trashed"))


# ─────────────────────────────────────────────────────────────
# 메인 UI 함수
# ─────────────────────────────────────────────────────────────
def display_photos_media(parent: tk.Widget, backup_path: str) -> None:
    for w in parent.winfo_children():
        w.destroy()

    header_frame = ttk.Frame(parent)
    header_frame.pack(fill="x")
    ttk.Label(header_frame, text="🖼️ Camera Roll Media", style="ContentHeader.TLabel").pack(side="left")

    style = ttk.Style(parent)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Filter.TButton", padding=6, relief="flat")
    style.map(
        "Filter.TButton",
        background=[("pressed", "#88B6FF")],
        foreground=[("pressed", "black")],
    )

    btn_frame = ttk.Frame(header_frame)
    btn_frame.pack(side="right")
    filter_state = {"mode": "total"}
    btn_total   = ttk.Button(btn_frame, text="Total Image",   style="Filter.TButton")
    btn_deleted = ttk.Button(btn_frame, text="Deleted Image", style="Filter.TButton")
    btn_total.pack(side="left", padx=(0, 4))
    btn_deleted.pack(side="left")
    btn_total.state(["pressed"])
    ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(0, 10))

    canvas_frame = ttk.Frame(parent)
    canvas_frame.pack(fill="both", expand=True)
    canvas = tk.Canvas(canvas_frame, highlightthickness=0, bg="white")
    vsb = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    grid_frame = tk.Frame(canvas, bg="white")
    grid_window = canvas.create_window((0, 0), window=grid_frame, anchor="nw")

    def _center_grid(_=None):
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        gw = grid_frame.winfo_reqwidth()
        gh = grid_frame.winfo_reqheight()

        x = max((cw - gw) // 2, 0)
        y = max((ch - gh) // 2, 0)
        canvas.coords(grid_window, x, y)

    grid_frame.bind(
        "<Configure>",
        lambda e: (
            canvas.configure(
                scrollregion=(0, 0, grid_frame.winfo_reqwidth(), grid_frame.winfo_reqheight())
            ),
            _center_grid(),
        ),
    )

    canvas.bind("<Configure>", _center_grid)

    nav_frame = ttk.Frame(parent)
    nav_frame.pack(fill="x", pady=(6, 4))
    nav_prev = ttk.Button(nav_frame, text="← Previous")
    nav_label = ttk.Label(nav_frame, text="0 / 0", style="InfoLabel.TLabel")
    nav_next = ttk.Button(nav_frame, text="Next →")
    nav_prev.pack(side="left", padx=10)
    nav_label.pack(side="left", expand=True)
    nav_next.pack(side="right", padx=10)

    state: Dict[str, Any] = {
        "items_total": [],
        "items_deleted": [],
        "items": [],
        "page": 0,
        "thumbs": {},
        "empty_lbl": None
    }

    def _show_empty_msg():
        """캔버스 정중앙에 안내 문구 배치"""
        if state["empty_lbl"] is None:
            lbl = tk.Label(
                canvas,
                text="No media items.",
                fg="gray",
                font=("Segoe UI", 14, "italic"),
                bg="white",
            )
            # place(relx/rely=0.5) → 창 크기 바뀌어도 자동 중앙
            lbl.place(relx=0.5, rely=0.5, anchor="center")
            state["empty_lbl"] = lbl
        else:
            state["empty_lbl"].place(relx=0.5, rely=0.5, anchor="center")


    def _hide_empty_msg():
        lbl = state.get("empty_lbl")
        if lbl:
            lbl.place_forget()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

    # ─────────────────────────── 미디어 감지 ───────────────────────────
    def _is_video(path: Path, fname: str) -> bool:
        ext_path = path.suffix.lower()
        ext_name = Path(fname).suffix.lower()
        return ext_path in VID_EXTS or ext_name in VID_EXTS

    def _is_image(path: Path, fname: str) -> bool:
        ext_path = path.suffix.lower()
        ext_name = Path(fname).suffix.lower()
        return ext_path in IMG_EXTS or ext_name in IMG_EXTS

    # ─────────────────────────── 스캐닝 스레드 ─────────────────────────
    def _scan():
        items = list(_enumerate_media_files(Path(backup_path)))
        state["items_total"] = [(p, f) for p, f, _del in items]
        state["items_deleted"] = [(p, f) for p, f, _del in items if _del]
        parent.after(0, _apply_filter)

    threading.Thread(target=_scan, daemon=True).start()

    # ─────────────────────────── 디코딩 / 썸네일 ─────────────────────
    def _load_image(path: Path) -> Image.Image:
        ext = path.suffix.lower()
        if ext == ".dng":
            with rawpy.imread(str(path)) as raw:
                return Image.fromarray(raw.postprocess())
        if ext == ".heic":
            if "heif" not in Image.OPEN:
                try:
                    from pillow_heif import register_heif_opener
                    register_heif_opener()
                except ModuleNotFoundError:
                    pass
        return Image.open(path)

    def _video_thumb_preview(path: Path) -> Image.Image | None:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame)

    def _video_thumb_pipe(path: Path) -> Image.Image | None:
        ffmpeg = os.environ["IMAGEIO_FFMPEG_EXE"]
        cmd = [
            ffmpeg,
            "-loglevel",
            "error",
            "-nostdin",
            "-ss",
            "0.5",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-f",
            "image2",
            "-c:v",
            "mjpeg",
            "pipe:1",
        ]
        try:
            with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
                data = proc.stdout.read()
            if data:
                return Image.open(io.BytesIO(data))
        except Exception:
            return None
        return None

    def _video_thumb_temp(path: Path) -> Image.Image | None:
        ffmpeg = os.environ["IMAGEIO_FFMPEG_EXE"]
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_name = tmp.name
        cmd = [
            ffmpeg,
            "-loglevel",
            "error",
            "-nostdin",
            "-ss",
            "0.5",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            tmp_name,
        ]
        if subprocess.call(cmd) == 0 and Path(tmp_name).exists():
            try:
                img = Image.open(tmp_name)
                img.load()
                return img
            finally:
                os.unlink(tmp_name)
        os.unlink(tmp_name)
        return None

    def _video_thumbnail(path: Path) -> Image.Image:
        for extractor in (_video_thumb_preview, _video_thumb_pipe, _video_thumb_temp):
            try:
                img = extractor(path)
                if img is not None:
                    break
            except Exception:
                continue
        else:
            img = Image.new("RGB", (THUMB_SIDE, THUMB_SIDE), "black")
        img.thumbnail((THUMB_SIDE, THUMB_SIDE))
        return img

    def _generate_thumbnail_image(path: Path, fname: str) -> Image.Image:
        try:
            if _is_video(path, fname):
                pil_img = _video_thumbnail(path)
            elif _is_image(path, fname):
                pil_img = _load_image(path)
                pil_img.thumbnail((THUMB_SIDE, THUMB_SIDE))
            else:
                raise ValueError("Unsupported format")
        except Exception:
            pil_img = Image.new("RGB", (THUMB_SIDE, THUMB_SIDE), "gray")
        return pil_img

    def _store_photoimage(path: Path, pil_img: Image.Image):
        if path not in state["thumbs"]:
            state["thumbs"][path] = ImageTk.PhotoImage(pil_img)

    def _preload_task(path: Path, fname: str):
        img = _generate_thumbnail_image(path, fname)
        parent.after(0, lambda: _store_photoimage(path, img))

    def _thumb(path: Path, fname: str):
        cache = state["thumbs"]
        if path in cache:
            return cache[path]
        img = _generate_thumbnail_image(path, fname)
        photo = ImageTk.PhotoImage(img)
        cache[path] = photo
        return photo

    def _save_file(src: Path, save_name: str):
        dest = filedialog.asksaveasfilename(initialfile=save_name)
        if dest:
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
                    fdst.write(fsrc.read())
            except Exception as e:
                messagebox.showerror("Save error", str(e))

    def _clear_grid():
        for child in grid_frame.grid_slaves():
            child.destroy()

    def _render_page():
        total_items = len(state["items"])

        if total_items == 0:
            _clear_grid()
            _show_empty_msg()

            nav_label.config(text="0 / 0")
            nav_prev.config(state="disabled")
            nav_next.config(state="disabled")
            return
        else:
            _hide_empty_msg()

        total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE
        state["page"] = max(0, min(state["page"], total_pages - 1))
        start = state["page"] * PAGE_SIZE
        end = min(start + PAGE_SIZE, total_items)

        _clear_grid()
        for idx, (p, fname) in enumerate(state["items"][start:end]):
            r, c = divmod(idx, COLS)
            cell = tk.Frame(grid_frame, bg="white", padx=2, pady=2)
            cell.grid(row=r, column=c, padx=4, pady=4, sticky="nw")
            thumb_box = tk.Frame(cell, width=THUMB_SIDE, height=THUMB_SIDE, bg="white")
            thumb_box.pack_propagate(False)
            thumb_box.pack()
            photo = _thumb(p, fname)
            lbl = tk.Label(thumb_box, image=photo, bg="white")
            lbl.image = photo
            lbl.pack(expand=True, anchor="center")
            lbl.bind("<Button-3>", lambda e, src=p, name=fname: _save_file(src, name))
            tk.Label(
                cell,
                text=fname,
                bg="white",
                wraplength=THUMB_SIDE,
                justify="center",
            ).pack(pady=(2, 0))

        nav_label.config(text=f"{state['page'] + 1} / {total_pages}")
        nav_prev.config(state="normal" if state["page"] > 0 else "disabled")
        nav_next.config(
            state="normal" if state["page"] < total_pages - 1 else "disabled"
        )
        parent.after(100, _preload_adjacent_pages)

    def _set_page(new_page: int):
        state["page"] = new_page
        _render_page()

    nav_prev.config(command=lambda: _set_page(state["page"] - 1))
    nav_next.config(command=lambda: _set_page(state["page"] + 1))

    # 인접 페이지 미리 로드
    def _preload_adjacent_pages():
        total_items = len(state["items"])
        total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE
        if total_pages <= 5:
            return
        preload_range = 5
        current = state["page"]
        start_p = max(0, current - preload_range)
        end_p = min(total_pages, current + preload_range + 1)
        for page in range(start_p, end_p):
            if page == current:
                continue
            page_start = page * PAGE_SIZE
            page_end = min(page_start + PAGE_SIZE, total_items)
            for p, fname in state["items"][page_start:page_end]:
                if p not in state["thumbs"]:
                    executor.submit(_preload_task, p, fname)

    def _apply_filter(reset_page: bool = True):
        mode = filter_state["mode"]
        state["items"] = state["items_total"] if mode == "total" else state["items_deleted"]

        if reset_page:
            state["page"] = 0
            canvas.yview_moveto(0)

        _render_page()

        # 상태 토글 → pressed 가 적용되면 배경색도 자동 변경
        btn_total.state(["pressed"]  if mode == "total"  else ["!pressed"])
        btn_deleted.state(["pressed"] if mode == "deleted" else ["!pressed"])

    def _choose_total():
        filter_state["mode"] = "total"
        _apply_filter()

    def _choose_deleted():
        filter_state["mode"] = "deleted"
        _apply_filter()

    btn_total.config(command=_choose_total)
    btn_deleted.config(command=_choose_deleted)

    _scan()


# ─────────────────────────────────────────────────────────────
# 백업 DB 탐색
# ─────────────────────────────────────────────────────────────
def _enumerate_media_files(backup_root: Path):
    manifest = backup_root / "Manifest.db"
    if not manifest.exists():
        return

    conn = sqlite3.connect(manifest)
    cur = conn.cursor()
    query = (
        "SELECT fileID, relativePath, file FROM Files "
        "WHERE domain LIKE '%CameraRollDomain%' "
        "AND relativePath LIKE '%Media/DCIM%' AND ("
        "relativePath LIKE '%.png'  COLLATE NOCASE OR relativePath LIKE '%.jpg'  COLLATE NOCASE OR "
        "relativePath LIKE '%.jpeg' COLLATE NOCASE OR relativePath LIKE '%.heic' COLLATE NOCASE OR "
        "relativePath LIKE '%.dng'  COLLATE NOCASE OR relativePath LIKE '%.mov'  COLLATE NOCASE OR "
        "relativePath LIKE '%.mp4'  COLLATE NOCASE)"
    )
    for file_id, rel, blob in cur.execute(query):
        real_path = backup_root / file_id[:2] / file_id
        if real_path.exists():
            is_deleted = _is_trashed_blob(blob) if blob else False
            yield real_path, Path(rel).name, is_deleted
    conn.close()
