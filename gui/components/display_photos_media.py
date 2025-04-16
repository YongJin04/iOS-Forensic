from __future__ import annotations
"""display_photos_media.py – ultra‑robust thumbnail gallery

*   **HEIC / DNG** stills are decoded via *pillow‑heif* or *rawpy*.
*   **MOV / MP4** clips always yield a thumbnail through a 3‑tier fallback:
    1. OpenCV → first frame (preview.py logic)
    2. ffmpeg → JPEG piped to memory
    3. ffmpeg → JPEG to temp file
*   Thumbnails are now **centered** inside a fixed‑size square so that
    small images no longer hug the top‑left corner.
"""

import io
import os
import sqlite3
import subprocess
import tempfile
import threading
import concurrent.futures
from pathlib import Path
from typing import List, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2  # runtime dep
import rawpy  # runtime dep
import imageio_ffmpeg  # runtime dep – bundles a static ffmpeg binary
from PIL import Image, ImageTk

os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()

try:
    from pillow_heif import register_heif_opener  # type: ignore
    register_heif_opener()
except ModuleNotFoundError:
    pass

COLS, ROWS = 6, 4
PAGE_SIZE = COLS * ROWS
THUMB_SIDE = 120

IMG_EXTS = {".png", ".jpg", ".jpeg", ".heic", ".dng"}
VID_EXTS = {".mov", ".mp4"}


def display_photos_media(parent: tk.Widget, backup_path: str) -> None:
    for w in parent.winfo_children():
        w.destroy()

    ttk.Label(parent, text="🖼️ Camera Roll Media", style="ContentHeader.TLabel").pack(anchor="w", pady=(0, 6))
    ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(0, 10))

    canvas_frame = ttk.Frame(parent)
    canvas_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(canvas_frame, highlightthickness=0, bg="white")
    vsb = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    # grid_frame을 캔버스 중앙에 배치
    grid_frame = tk.Frame(canvas, bg="white")
    grid_window = canvas.create_window((0, 0), window=grid_frame, anchor="center")
    grid_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def center_grid(event):
        canvas.coords(grid_window, event.width / 2, event.height / 2)
    canvas.bind("<Configure>", center_grid)

    nav_frame = ttk.Frame(parent)
    nav_frame.pack(fill="x", pady=(6, 4))
    nav_prev = ttk.Button(nav_frame, text="← Previous")
    nav_label = ttk.Label(nav_frame, text="0 / 0", style="InfoLabel.TLabel")
    nav_next = ttk.Button(nav_frame, text="Next →")
    nav_prev.pack(side="left", padx=10)
    nav_label.pack(side="left", expand=True)
    nav_next.pack(side="right", padx=10)

    state: dict = {"items": [], "page": 0, "thumbs": {}}

    # 백그라운드에서 인접 페이지의 썸네일을 생성하기 위해 ThreadPoolExecutor 사용 (최대 8 스레드)
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

    # ─────────────────────────────────────────────────────────────
    # 미디어 형식 감지 헬퍼 함수들
    # ─────────────────────────────────────────────────────────────
    def _is_video(path: Path, fname: str) -> bool:
        ext_path = path.suffix.lower()
        ext_name = Path(fname).suffix.lower()
        return ext_path in VID_EXTS or ext_name in VID_EXTS

    def _is_image(path: Path, fname: str) -> bool:
        ext_path = path.suffix.lower()
        ext_name = Path(fname).suffix.lower()
        return ext_path in IMG_EXTS or ext_name in IMG_EXTS

    # ─────────────────────────────────────────────────────────────
    def _scan():
        state["items"] = list(_enumerate_media_files(Path(backup_path)))
        parent.after(0, _render_page)

    threading.Thread(target=_scan, daemon=True).start()

    # ─────────────────────────────────────────────────────────────
    # 이미지 / 비디오 디코딩 함수들
    # ─────────────────────────────────────────────────────────────
    def _load_image(path: Path) -> Image.Image:
        ext = path.suffix.lower()
        if ext == ".dng":
            with rawpy.imread(str(path)) as raw:
                return Image.fromarray(raw.postprocess())
        if ext == ".heic":
            if "heif" not in Image.OPEN:
                try:
                    from pillow_heif import register_heif_opener  # type: ignore
                    register_heif_opener()
                except ModuleNotFoundError:
                    pass
        return Image.open(path)

    def _video_thumb_preview_style(path: Path) -> Image.Image | None:
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
        cmd = [ffmpeg, "-loglevel", "error", "-nostdin", "-ss", "0.5", "-i", str(path),
               "-frames:v", "1", "-f", "image2", "-c:v", "mjpeg", "pipe:1"]
        try:
            with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
                data = proc.stdout.read()
            if data:
                return Image.open(io.BytesIO(data))
        except Exception:
            return None
        return None

    def _video_thumb_tempfile(path: Path) -> Image.Image | None:
        ffmpeg = os.environ["IMAGEIO_FFMPEG_EXE"]
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_name = tmp.name
        cmd = [ffmpeg, "-loglevel", "error", "-nostdin", "-ss", "0.5", "-i", str(path),
               "-frames:v", "1", "-q:v", "2", tmp_name]
        if subprocess.call(cmd) == 0 and Path(tmp_name).exists():
            try:
                img = Image.open(tmp_name)
                img.load()
                return img
            finally:
                os.unlink(tmp_name)
        else:
            os.unlink(tmp_name)
        return None

    def _video_thumbnail(path: Path) -> Image.Image:
        for extractor in (_video_thumb_preview_style, _video_thumb_pipe, _video_thumb_tempfile):
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

    # ─────────────────────────────────────────────────────────────
    # 무거운 작업(디코딩, 썸네일 생성)만 수행하여 PIL 이미지 반환하는 함수
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

    # 메인 스레드에서 PhotoImage 생성 후 캐시에 저장
    def _store_photoimage(path: Path, pil_img: Image.Image):
        if path not in state["thumbs"]:
            photo = ImageTk.PhotoImage(pil_img)
            state["thumbs"][path] = photo

    # 백그라운드에서 호출되는 미리 로드 작업 함수
    def _preload_task(path: Path, fname: str):
        pil_img = _generate_thumbnail_image(path, fname)
        parent.after(0, lambda: _store_photoimage(path, pil_img))

    # ─────────────────────────────────────────────────────────────
    # 썸네일 캐시 및 생성 (동일한 _thumb 함수는 페이지 렌더링 시 사용)
    def _thumb(path: Path, fname: str) -> ImageTk.PhotoImage:
        cache = state["thumbs"]
        if path in cache:
            return cache[path]
        try:
            if _is_video(path, fname):
                img = _video_thumbnail(path)
            elif _is_image(path, fname):
                img = _load_image(path)
                img.thumbnail((THUMB_SIDE, THUMB_SIDE))
            else:
                raise ValueError("Unsupported format")
        except Exception:
            img = Image.new("RGB", (THUMB_SIDE, THUMB_SIDE), "gray")
        photo = ImageTk.PhotoImage(img)
        cache[path] = photo
        return photo

    # ─────────────────────────────────────────────────────────────
    # 파일 저장 헬퍼 함수
    def _save_file(src: Path, save_name: str):
        dest = filedialog.asksaveasfilename(initialfile=save_name)
        if dest:
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
                    fdst.write(fsrc.read())
            except Exception as e:
                messagebox.showerror("Save error", str(e))

    # ─────────────────────────────────────────────────────────────
    def _clear_grid():
        for child in grid_frame.grid_slaves():
            child.destroy()

    # ─────────────────────────────────────────────────────────────
    # 페이지 렌더링 함수 (현재 페이지의 썸네일을 표시)
    def _render_page():
        total_items = len(state["items"])
        if total_items == 0:
            nav_label.config(text="0 / 0")
            return
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
            # 썸네일 이미지를 중앙 정렬
            lbl.pack(expand=True, anchor="center")
            lbl.bind("<Button-3>", lambda e, src=p, name=fname: _save_file(src, name))
            tk.Label(cell, text=fname, bg="white", wraplength=THUMB_SIDE, justify="center").pack(pady=(2, 0))
        nav_label.config(text=f"{state['page'] + 1} / {total_pages}")
        nav_prev.config(state="normal" if state["page"] > 0 else "disabled")
        nav_next.config(state="normal" if state["page"] < total_pages - 1 else "disabled")
        # 현재 페이지 주변 양옆 최대 5페이지의 썸네일을 미리 로드 (전체 페이지가 5개 초과일 때)
        parent.after(100, _preload_adjacent_pages)

    nav_prev.config(command=lambda: _set_page(state["page"] - 1))
    nav_next.config(command=lambda: _set_page(state["page"] + 1))

    def _set_page(new_page: int):
        state["page"] = new_page
        _render_page()

    # ─────────────────────────────────────────────────────────────
    # 인접 페이지(양옆 최대 5페이지) 썸네일 미리 로드 함수 (백그라운드 스레드에서 수행)
    def _preload_adjacent_pages():
        total_items = len(state["items"])
        total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE
        if total_pages <= 5:
            return
        preload_range = 5
        current = state["page"]
        start_page = max(0, current - preload_range)
        end_page = min(total_pages, current + preload_range + 1)
        for page in range(start_page, end_page):
            if page == current:
                continue
            page_start = page * PAGE_SIZE
            page_end = min(page_start + PAGE_SIZE, total_items)
            for p, fname in state["items"][page_start:page_end]:
                if p not in state["thumbs"]:
                    executor.submit(_preload_task, p, fname)


def _enumerate_media_files(backup_root: Path):
    manifest = backup_root / "Manifest.db"
    if not manifest.exists():
        return
    conn = sqlite3.connect(manifest)
    cur = conn.cursor()
    query = (
        "SELECT fileID, relativePath FROM Files WHERE domain LIKE '%CameraRollDomain%' "
        "AND relativePath LIKE '%Media/DCIM%' AND ("
        "relativePath LIKE '%.png'  COLLATE NOCASE OR relativePath LIKE '%.jpg'  COLLATE NOCASE OR "
        "relativePath LIKE '%.jpeg' COLLATE NOCASE OR relativePath LIKE '%.heic' COLLATE NOCASE OR "
        "relativePath LIKE '%.dng'  COLLATE NOCASE OR relativePath LIKE '%.mov'  COLLATE NOCASE OR "
        "relativePath LIKE '%.mp4'  COLLATE NOCASE)"
    )
    for file_id, rel in cur.execute(query):
        real_path = backup_root / file_id[:2] / file_id
        if real_path.exists():
            yield real_path, Path(rel).name
    conn.close()
