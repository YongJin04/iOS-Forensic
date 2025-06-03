import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from pathlib import Path
import os
import subprocess

import pygame          # 오디오 재생
from PIL import Image, ImageTk  # 이미지 (향후 확장 대비)

from artifact_analyzer.notes.notes_analyser import NotesAnalyser


# ────────────────────────────────────────────────────────────────────────────
# 미디어 전용 하위 창
# ────────────────────────────────────────────────────────────────────────────
class MediaWindow(Toplevel):
    """선택한 오디오‧비디오 파일을 재생하기 위한 임시 창"""

    def __init__(self, master, file_path, mime_type):
        super().__init__(master)
        self.title("미디어 재생")
        self.geometry("400x300")

        self.file_path = file_path
        self.mime_type = mime_type or ""
        self.playing = False
        self.audio_mixer = None

        ext = Path(file_path).suffix.lower()
        is_video = ("quicktime" in self.mime_type) or ext in {".mov", ".mp4"}
        is_audio = self.mime_type.startswith("audio/") or ext in {".m4a", ".mp3"}

        if is_video:
            self._display_video_controls()
        elif is_audio:
            self._display_audio_controls()
        else:
            ttk.Label(self, text="지원하지 않는 미디어 형식").pack(padx=10, pady=10)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 비디오: 외부 플레이어 열기 ────────────────────────────────────────
    def _display_video_controls(self):
        ttk.Label(self, text=os.path.basename(self.file_path)).pack(pady=10)
        ttk.Button(self, text="외부 플레이어로 열기", command=self._open_external).pack()

    def _open_external(self):
        try:
            if os.name == "nt":
                os.startfile(self.file_path)
            elif os.name == "posix":
                subprocess.run(["open", self.file_path], check=True)
            else:
                messagebox.showerror("오류", "외부 재생을 지원하지 않는 OS 입니다.")
        except Exception as e:
            messagebox.showerror("오류", f"비디오 재생 오류: {e}")

    # ── 오디오: 재생/정지 ────────────────────────────────────────────────
    def _display_audio_controls(self):
        self.play_btn = ttk.Button(self, text="▶️ 재생", command=self._toggle_audio)
        self.play_btn.pack(pady=10)
        ttk.Label(self, text=os.path.basename(self.file_path)).pack()

    def _toggle_audio(self):
        if not self.playing:
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(self.file_path)
                pygame.mixer.music.play()
                self.play_btn.config(text="⏸️ 정지")
                self.playing = True
                self.audio_mixer = pygame.mixer
            except pygame.error as e:
                messagebox.showerror("오디오 재생 오류", str(e))
        else:
            pygame.mixer.music.stop()
            self.play_btn.config(text="▶️ 재생")
            self.playing = False

    # ── 창 종료 ─────────────────────────────────────────────────────────
    def _on_close(self):
        if self.audio_mixer and self.playing:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        self.destroy()


# ────────────────────────────────────────────────────────────────────────────
# 메인: 노트 리스트 & 상세
# ────────────────────────────────────────────────────────────────────────────
def display_notes(content_frame: ttk.Frame, backup_path: str):
    """Notes GUI 메인 진입점 (Title 검색 + 본문 전체 표시)"""

    # ― 이전 위젯 정리
    for w in content_frame.winfo_children():
        w.destroy()

    # ― 헤더
    header = ttk.Frame(content_frame)
    header.pack(fill="x", pady=(0, 10))
    ttk.Label(header, text="📝 Notes", style="ContentHeader.TLabel").pack(side="left")
    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))

    # ― 좌/우 컨테이너
    container = ttk.Frame(content_frame); container.pack(fill="both", expand=True)

    # ────────────────────────────────────────────────────────────────
    # ① 왼쪽: 검색 바 + 노트 목록
    # ────────────────────────────────────────────────────────────────
    left = ttk.Frame(container); left.pack(side="left", fill="both", padx=(0, 5))

    # ①-A. 검색 바  (Title 검색)
    search_bar = ttk.Frame(left)
    search_bar.pack(fill="x", pady=(0, 6))
    ttk.Label(search_bar, text="Search Title:").pack(side="left")

    kw_var = tk.StringVar()
    ent_search = ttk.Entry(search_bar, textvariable=kw_var, width=32)
    ent_search.pack(side="left", padx=4)

    btn_search = ttk.Button(search_bar, text="검색")
    btn_search.pack(side="left", padx=4)

    # ①-B. 트리뷰
    tree_frame = ttk.Frame(left); tree_frame.pack(fill="both", expand=True)

    notes_tree = ttk.Treeview(
        tree_frame,
        columns=("title", "created", "modified"),
        show="headings",
        selectmode="browse",
    )
    notes_tree.heading("title",    text="Title")
    notes_tree.heading("created",  text="Created At")
    notes_tree.heading("modified", text="Modified At")

    notes_tree.column("title",    width=180)
    notes_tree.column("created",  width=115)
    notes_tree.column("modified", width=115)
    notes_tree.pack(side="left", fill="both", expand=True)

    # 스크롤바
    yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=notes_tree.yview)
    notes_tree.configure(yscrollcommand=yscroll.set)
    yscroll.pack(side="right", fill="y")

    # 스트라이프 배경
    notes_tree.tag_configure("oddrow",  background="white")
    notes_tree.tag_configure("evenrow", background="#F5F5F5")

    # ────────────────────────────────────────────────────────────────
    # ② 오른쪽: 상세 뷰
    # ────────────────────────────────────────────────────────────────
    right = ttk.Frame(container); right.pack(side="right", fill="both", expand=True, padx=(5, 0))
    detail = ttk.Frame(right); detail.pack(fill="both", expand=True)

    #  제목(선택된 노트의 Title)
    title_label = ttk.Label(detail, text="", style="Bold.TLabel")
    title_label.pack(anchor="w")

    #  본문
    note_text = tk.Text(detail, wrap="word", state="disabled")
    note_text.pack(fill="both", expand=True)

    scroll = ttk.Scrollbar(detail, orient="vertical", command=note_text.yview)
    note_text.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")

    # 미디어 재생 버튼(필요 시 활성화)
    btn_frame = ttk.Frame(detail); btn_frame.pack(anchor="w", pady=(10, 0))
    play_media_btn = ttk.Button(btn_frame, text="▶️ 미디어 재생", state=tk.DISABLED)
    play_media_btn.pack(side="left")

    # ────────────────────────────────────────────────────────────────
    # 데이터 준비
    # ────────────────────────────────────────────────────────────────
    analyser = NotesAnalyser(backup_path)
    all_df = analyser.get_all_notes()

    # ── 트리뷰 채우기 ───────────────────────────
    def populate(df):
        notes_tree.delete(*notes_tree.get_children())
        for idx, row in df.iterrows():
            row_tag = "evenrow" if idx % 2 else "oddrow"
            notes_tree.insert(
                "",
                "end",
                values=(row["title"], row["created_at_kst"], row["modified_at_kst"]),
                tags=(row["uuid"], row.get("mime_type", ""), row_tag),
            )

    # ── 상세 표시 (본문 전체) ─────────────────────
    def show_detail(event):
        sel = notes_tree.selection()
        if not sel:
            play_media_btn.config(state=tk.DISABLED)
            return

        tags = notes_tree.item(sel[0], "tags")
        uuid = tags[0] if len(tags) > 0 else None
        mime = tags[1] if len(tags) > 1 else None

        if not uuid:
            return

        note = analyser.get_note_detail(uuid)

        # ① 타이틀
        title_label.config(text=note.get("title", ""))

        # ② 본문 (전체 content 사용)  ← FIXED
        note_text.config(state="normal")
        note_text.delete("1.0", tk.END)
        note_text.insert(tk.END, note.get("content", note.get("내용 미리보기", "")))
        note_text.config(state="disabled")

        # ③ 미디어 버튼 세팅 (첨부파일 처리 시 활용)
        play_media_btn.uuid = uuid
        play_media_btn.mime_type = mime
        play_media_btn.filename = note.get("filename")
        play_media_btn.config(state=tk.NORMAL)

    # ── Manifest → 실제 파일 경로 ───────────────
    def _manifest_lookup(uuid: str, filename: str) -> str | None:
        import sqlite3
        manifest = Path(backup_path) / "Manifest.db"
        if not manifest.exists():
            return None
        try:
            with sqlite3.connect(str(manifest)) as conn:
                cur = conn.cursor()
                like = f"%{uuid}%{filename}%"
                cur.execute(
                    """
                    SELECT fileID FROM Files
                    WHERE domain='AppDomainGroup-group.com.apple.notes'
                      AND relativePath LIKE ?
                    """,
                    (like,),
                )
                row = cur.fetchone()
            if not row:
                return None
            file_id = row[0]
            path = Path(backup_path) / file_id[:2] / file_id
            return str(path) if path.exists() else None
        except Exception:
            return None

    # ── 미디어 재생 ─────────────────────────────
    def play_media():
        uuid = getattr(play_media_btn, "uuid", None)
        mime = getattr(play_media_btn, "mime_type", None)
        fname = getattr(play_media_btn, "filename", None)

        if not uuid or not fname:
            messagebox.showerror("오류", "선택된 노트가 없거나 첨부파일 정보가 없습니다.")
            return

        if not mime or mime == "None":
            ext = Path(fname).suffix.lower()
            mime = (
                "video/quicktime" if ext == ".mov"
                else "audio/mp4"     if ext == ".m4a"
                else "image/png"    if ext == ".png"
                else "application/octet-stream"
            )

        real_path = _manifest_lookup(uuid, fname)
        if real_path and Path(real_path).exists():
            MediaWindow(content_frame, real_path, mime)
        else:
            messagebox.showinfo("알림", "미디어 파일을 찾을 수 없습니다.")

    # ── Title 검색 ─────────────────────────────
    def do_search(_e=None):
        kw = kw_var.get().strip().lower()
        if not kw:
            populate(all_df)
            return
        filtered = all_df[all_df["title"].str.lower().str.contains(kw, na=False)]
        populate(filtered)

    # ── 이벤트 & 초기화 ─────────────────────────
    populate(all_df)

    notes_tree.bind("<<TreeviewSelect>>", show_detail)
    play_media_btn.config(command=play_media)
    btn_search.configure(command=do_search)
    ent_search.bind("<Return>", do_search)

    # ― 스타일
    style = ttk.Style()
    style.configure("Bold.TLabel", font=("Helvetica", 12, "bold"))
