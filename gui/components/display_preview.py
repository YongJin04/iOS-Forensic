# preview.py
"""
PreviewManager
--------------
파일‑리스트 Treeview 선택 시 이미지/동영상을 라벨에 미리보여 줍니다.
(main_windows.py 에서 import 하여 사용)

추가 기능:
- 이미지/비디오 확장자가 아닐 경우, 16바이트 단위의 Hex Dump+Decoded Text 뷰어 표시
- AAE 확장자도 Hex 뷰어로 표시
- 스크롤바를 이용해 긴 Hex 내용을 스크롤 가능
- Offset, Hex 값, Decoded Text 헤더 표시
"""
from __future__ import annotations
import os, sqlite3, xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional

import tkinter as tk
import tkinter.ttk as ttk
import cv2, rawpy, imageio_ffmpeg
from PIL import Image, ImageTk

class PreviewManager:
    # AAE 제거 -> aae는 Hex 뷰어로 표시
    IMG_EXTS = {"png", "jpg", "jpeg", "heic", "dng"}  
    VID_EXTS = {"mov", "mp4"}

    def __init__(
        self,
        *,
        preview_label: tk.Label,
        file_list_tree: ttk.Treeview,
        backup_path_var: tk.StringVar,
    ) -> None:
        self.preview_label   = preview_label
        self.file_list_tree  = file_list_tree
        self.backup_path_var = backup_path_var
        self._video_state: Dict[str, Optional[object]] = {"cap": None, "job": None}

        os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()
        file_list_tree.bind("<<TreeviewSelect>>", self.preview_selected, add="+")

        # ─── Hex Frame (Text + Scrollbar) 초기화 ─────────────────────────
        # preview_label와 같은 부모에 두고, 필요 시에만 pack
        parent = self.preview_label.master
        self._hex_frame = tk.Frame(parent, bg="white")
        self._hex_scrollbar = tk.Scrollbar(self._hex_frame, orient="vertical")
        self._hex_text = tk.Text(
            self._hex_frame, 
            wrap="none",   # 자동 줄바꿈 없음
            yscrollcommand=self._hex_scrollbar.set
        )
        self._hex_scrollbar.config(command=self._hex_text.yview)
        self._hex_scrollbar.pack(side="right", fill="y")
        self._hex_text.pack(side="left", fill="both", expand=True)
        # 초기에는 숨겨둠
        self._hex_frame.pack_forget()

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

    # ────────────────────────── Hex View 관련 ──────────────────────────
    def _show_hexview(self, real_path: Path) -> None:
        """이미지/비디오 확장자가 아닌 파일(또는 AAE)의 내용을
           Hex Dump와 Decoded Text로 스크롤 가능하게 표시."""
        try:
            # 최대 2KB까지만 미리보기 (필요 시 조정 가능)
            max_bytes = 2048
            with open(real_path, "rb") as f:
                content = f.read(max_bytes + 1)
            truncated = len(content) > max_bytes
            if truncated:
                content = content[:max_bytes]

            # 헤더 + 헥스 덤프 생성
            hex_dump = self._format_hex_dump(content)
            if truncated:
                hex_dump += "\n... (truncated)"

            # preview_label 숨기고 hex_frame 보이게
            self.preview_label.pack_forget()
            self._hex_frame.pack(fill="both", expand=True)

            # Hex 내용을 Text 위젯에 삽입
            self._hex_text.delete("1.0", "end")
            self._hex_text.insert("1.0", hex_dump)
            self._hex_text.mark_set("insert", "1.0")
        except Exception as e:
            self._hex_text.delete("1.0", "end")
            self._hex_text.insert(
                "1.0", f"(Failed to display file in hex view.)\n{e}"
            )

    def _hide_hexview(self):
        """Hex 뷰어를 숨기고 preview_label 다시 보임."""
        self._hex_frame.pack_forget()
        self.preview_label.pack(fill="both", expand=True)

    def _format_hex_dump(self, data: bytes) -> str:
        """data를 받아 각 행 16바이트씩 Offset, Hex, Decoded Text 형식의 문자열 반환."""
        lines = []
        # 헤더 추가
        # Offset(h)   Hex 값(16 bytes)                       Decoded Text
        # (컬럼 폭은 상황에 맞게 적절히 조정)
        lines.append(f"{'Offset(h)':<10}{'00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F':<50}Decoded Text")
        lines.append("=" * 80)  # 구분선

        for offset in range(0, len(data), 16):
            chunk = data[offset : offset + 16]
            # 각 바이트를 두 자리 16진수로 표현 (공백으로 구분)
            hex_str = " ".join(f"{b:02X}" for b in chunk)
            # 출력 가능한 ASCII 문자는 그대로, 아니면 점(.)으로 표시
            ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            line = f"{offset:08X}: {hex_str:<48} {ascii_str}"
            lines.append(line)
        return "\n".join(lines)

    # ─── 메인 콜백 ───────────────────────────────────────────────
    def preview_selected(self, _event=None):
        sel = self.file_list_tree.selection()
        if not sel:
            return
        self._stop_video()

        logical_path = self.file_list_tree.item(sel[0], "values")[0]
        ext = Path(logical_path).suffix.lower().lstrip(".")

        try:
            domain, _, rel = logical_path.split("/", 2)
        except ValueError:
            return

        backup_path = Path(self.backup_path_var.get())
        mdb = backup_path / "Manifest.db"
        if not mdb.exists():
            return
        conn = sqlite3.connect(mdb)
        cur = conn.cursor()
        cur.execute(
            "SELECT fileID FROM Files WHERE domain=? AND relativePath=?",
            (domain, rel),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return
        real_path = backup_path / row[0][:2] / row[0]

        # Hex View 중이었다면 우선 숨긴다
        self._hide_hexview()

        if ext in self.IMG_EXTS:
            self._show_image(real_path, ext)
        elif ext in self.VID_EXTS:
            self._play_video(real_path)
        else:
            # AAE도 Hex 뷰로 표시
            self._show_hexview(real_path)

    # ─── 이미지 처리 ────────────────────────────────────────────
    def _show_image(self, real_path: Path, ext: str):
        try:
            img = self._load_image(real_path, ext)
            w = self.preview_label.winfo_width() or 400
            h = self.preview_label.winfo_height() or 300
            img.thumbnail((w, h))
            tk_img = ImageTk.PhotoImage(img)
            self.preview_label.config(image=tk_img, text="")
            self.preview_label.image = tk_img
        except Exception as e:
            self.preview_label.config(text=f"(Failed to open image.)\n{e}", image="")

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
                self._stop_video()
                return
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            w = self.preview_label.winfo_width() or 400
            h = self.preview_label.winfo_height() or 300
            img.thumbnail((w, h))
            tk_img = ImageTk.PhotoImage(img)
            self.preview_label.config(image=tk_img)
            self.preview_label.image = tk_img
            self._video_state["job"] = self.preview_label.after(33, _next)
        _next()

    # ─── 소멸자 ─────────────────────────────────────────────────
    def __del__(self):
        self._stop_video()
