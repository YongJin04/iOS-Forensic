# preview.py
"""
PreviewManager
--------------
파일‑리스트 Treeview 선택 시 이미지/동영상을 라벨에 미리보여 줍니다.
(main_windows.py 에서 import 하여 사용)
"""
from __future__ import annotations
import os, sqlite3, xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional

import tkinter as tk
import cv2, rawpy, imageio_ffmpeg
from PIL import Image, ImageTk


class PreviewManager:
    IMG_EXTS = {"png", "jpg", "jpeg", "heic", "aae", "dng"}
    VID_EXTS = {"mov", "mp4"}

    def __init__(
        self,
        *,
        preview_label: tk.Label,
        file_list_tree: tk.ttk.Treeview,
        backup_path_var: tk.StringVar,
    ) -> None:
        self.preview_label   = preview_label
        self.file_list_tree  = file_list_tree
        self.backup_path_var = backup_path_var
        self._video_state: Dict[str, Optional[object]] = {"cap": None, "job": None}

        os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()
        file_list_tree.bind("<<TreeviewSelect>>", self.preview_selected, add="+")

    # ─── 내부 유틸 ───────────────────────────────────────────────
    def _stop_video(self):
        if self._video_state["job"]:
            self.preview_label.after_cancel(self._video_state["job"])
            self._video_state["job"] = None
        if self._video_state["cap"]:
            self._video_state["cap"].release()
            self._video_state["cap"] = None

    @staticmethod
    def _load_image(path: Path, ext: str):
        if ext == "heic":
            from pillow_heif import register_heif_opener
            register_heif_opener()
            return Image.open(path)
        if ext == "dng":
            with rawpy.imread(str(path)) as raw:
                return Image.fromarray(raw.postprocess())
        return Image.open(path)

    # ─── 메인 콜백 ───────────────────────────────────────────────
    def preview_selected(self, _event=None):
        sel = self.file_list_tree.selection()
        if not sel:
            return
        self._stop_video()

        logical_path = self.file_list_tree.item(sel[0], "values")[0]
        ext = Path(logical_path).suffix.lower().lstrip(".")

        if ext not in (self.IMG_EXTS | self.VID_EXTS):
            self.preview_label.config(text="(Preview not supported.)", image="")
            return

        try:
            domain, _, rel = logical_path.split("/", 2)
        except ValueError:
            return

        mdb = Path(self.backup_path_var.get()) / "Manifest.db"
        if not mdb.exists():
            return
        conn = sqlite3.connect(mdb)
        cur = conn.cursor()
        cur.execute(
            "SELECT fileID FROM Files WHERE domain=? AND relativePath=?",
            (domain, rel),
        )
        row = cur.fetchone(); conn.close()
        if not row:
            return
        real_path = Path(self.backup_path_var.get()) / row[0][:2] / row[0]

        if ext in self.IMG_EXTS:
            self._show_image(real_path, ext)
        else:
            self._play_video(real_path)

    # ─── 이미지 처리 ────────────────────────────────────────────
    def _show_image(self, real_path: Path, ext: str):
        try:
            img = (
                self._resolve_aae(real_path) if ext == "aae"
                else self._load_image(real_path, ext)
            )
            w = self.preview_label.winfo_width() or 400
            h = self.preview_label.winfo_height() or 300
            img.thumbnail((w, h))
            tk_img = ImageTk.PhotoImage(img)
            self.preview_label.config(image=tk_img, text="")
            self.preview_label.image = tk_img
        except Exception as e:
            self.preview_label.config(text=f"(Failed to open image.)\n{e}", image="")

    def _resolve_aae(self, aae_path: Path):
        stem = aae_path.with_suffix("")
        for cand in (
            stem.with_suffix(".JPG"), stem.with_suffix(".jpg"),
            stem.with_suffix(".HEIC"), stem.with_suffix(".heic")
        ):
            if cand.exists():
                return self._load_image(cand, cand.suffix.lstrip("."))
        root = ET.parse(aae_path).getroot()
        base = root.find(".//adjustmentBaseImage").text
        return self._load_image(aae_path.parent / base, base.split(".")[-1])

    # ─── 동영상 처리 ─────────────────────────────────────────────
    def _play_video(self, real_path: Path):
        cap = cv2.VideoCapture(str(real_path))
        if not cap.isOpened():
            self.preview_label.config(text="(Failed to open video.)", image="")
            return
        self._video_state["cap"] = cap
        self.preview_label.config(text="", image="")

        def _next():
            ret, frame = cap.read()
            if not ret:
                self._stop_video(); return
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            w = self.preview_label.winfo_width() or 400
            h = self.preview_label.winfo_height() or 300
            img.thumbnail((w, h))
            tk_img = ImageTk.PhotoImage(img)
            self.preview_label.config(image=tk_img); self.preview_label.image = tk_img
            self._video_state["job"] = self.preview_label.after(33, _next)
        _next()

    # ─── 소멸자 ─────────────────────────────────────────────────
    def __del__(self):
        self._stop_video()
