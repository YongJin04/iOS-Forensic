import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from PIL import Image, ImageTk  # 이미지 처리를 위한 Pillow 라이브러리
import pygame  # 오디오 재생을 위한 Pygame 라이브러리
from artifact_analyzer.notes.notes_analyser import NotesAnalyser
import os
import subprocess  # 외부 프로그램 실행을 위한 subprocess 모듈
from pathlib import Path

class MediaWindow(Toplevel):
    def __init__(self, master, file_path, mime_type):
        super().__init__(master)
        self.title("미디어 재생")
        self.geometry("400x300")
        self.file_path = file_path
        self.mime_type = mime_type
        self.playing = False
        self.audio_mixer = None

        # 확장자 기반 비디오 판단 추가
        from pathlib import Path
        ext = Path(file_path).suffix.lower()
        is_video = (
            (mime_type and "quicktime" in mime_type)
            or ext in [".mov", ".mp4"]
        )
        is_audio = (
            (mime_type and mime_type.startswith("audio/"))
            or ext in [".m4a", ".mp3"]
        )

        if is_video:
            self.display_video_info()
        elif is_audio:
            self.display_audio_controls()
        else:
            ttk.Label(self, text="지원하지 않는 미디어 형식").pack(padx=10, pady=10)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """닫기 동작 처리"""
        if self.audio_mixer and self.playing:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        self.destroy()


    def play_audio(self):
        if not self.playing:
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(self.file_path)
                pygame.mixer.music.play()
                self.play_button.config(text="⏸️ 정지")
                self.playing = True
                self.audio_mixer = pygame.mixer
            except pygame.error as e:
                messagebox.showerror("오디오 재생 오류", f"오디오 재생 오류: {e}")
        else:
            pygame.mixer.music.stop()
            self.play_button.config(text="▶️ 재생")
            self.playing = False

    def display_audio_controls(self):
        self.play_button = ttk.Button(self, text="▶️ 재생", command=self.play_audio)
        self.play_button.pack(pady=10)
        ttk.Label(self, text=os.path.basename(self.file_path)).pack()

    def display_video_info(self):
        ttk.Label(self, text=f"비디오 파일: {os.path.basename(self.file_path)}").pack(pady=10)
        open_button = ttk.Button(self, text="외부 플레이어로 열기", command=self.open_video_externally)
        open_button.pack()

    def open_video_externally(self):
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.file_path)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.run(['open', self.file_path], check=True)
            else:
                messagebox.showerror("오류", "비디오 재생을 지원하지 않는 운영체제입니다.")
        except FileNotFoundError:
            messagebox.showerror("오류", f"비디오 파일을 찾을 수 없습니다: {self.file_path}")
        except Exception as e:
            messagebox.showerror("오류", f"비디오 재생 오류: {e}")

def display_notes(content_frame, backup_path):
    """
    노트 관련 UI를 표시하는 메인 함수

    Args:
        content_frame: UI를 표시할 프레임
        backup_path: 백업 파일 경로
    """
    # 기존 위젯 삭제
    for widget in content_frame.winfo_children():
        widget.destroy()

    # 헤더 추가
    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill="x", pady=(0, 10))

    ttk.Label(header_frame, text="📝 노트", style="ContentHeader.TLabel").pack(side="left")

    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))

    # 메인 컨테이너 프레임 (좌우 분할)
    main_container = ttk.Frame(content_frame)
    main_container.pack(fill="both", expand=True)

    # 왼쪽 프레임 (노트 목록)
    left_frame = ttk.Frame(main_container)
    left_frame.pack(side="left", fill="both", expand=False, padx=(0, 5))

    # 노트 목록을 표시할 Treeview
    notes_tree_frame = ttk.Frame(left_frame)
    notes_tree_frame.pack(fill="both", expand=True)

    notes_tree = ttk.Treeview(notes_tree_frame, columns=("title", "created_at", "modified_at", "type"), show="headings")
    notes_tree.heading("title", text="제목")
    notes_tree.heading("created_at", text="생성 시간")
    notes_tree.heading("modified_at", text="수정 시간")
    notes_tree.heading("type", text="형식")
    notes_tree.column("title", width=150)
    notes_tree.column("created_at", width=100)
    notes_tree.column("modified_at", width=100)
    notes_tree.column("type", width=50)
    notes_tree.pack(side="left", fill="both", expand=True)

    # 스크롤바 추가
    notes_scrollbar = ttk.Scrollbar(notes_tree_frame, orient="vertical", command=notes_tree.yview)
    notes_tree.configure(yscrollcommand=notes_scrollbar.set)
    notes_scrollbar.pack(side="right", fill="y")

    # 오른쪽 프레임 (노트 상세 내용)
    right_frame = ttk.Frame(main_container)
    right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

    # 노트 상세 내용 영역
    detail_frame = ttk.Frame(right_frame)
    detail_frame.pack(fill="both", expand=True)

    ttk.Label(detail_frame, text="노트 상세 내용:", style="Bold.TLabel").pack(anchor="w")

    note_text = tk.Text(detail_frame, wrap="word", state="disabled")
    note_text.pack(fill="both", expand=True)

    note_text_scrollbar = ttk.Scrollbar(detail_frame, orient="vertical", command=note_text.yview)
    note_text.configure(yscrollcommand=note_text_scrollbar.set)
    note_text_scrollbar.pack(side="right", fill="y")

    # NotesAnalyser 인스턴스 생성
    notes_analyser = NotesAnalyser(backup_path)

    def populate_notes_list():
        """노트 목록을 Treeview에 채우는 함수"""
        notes_df = notes_analyser.get_all_notes()
        if not notes_df.empty:
            for index, row in notes_df.iterrows():
                note_type = "텍스트"
                if row['mime_type'] and row['mime_type'].startswith("com.apple.quicktime-movie"):
                    note_type = "비디오"
                elif row['mime_type'] and row['mime_type'].startswith("com.apple.m4a-audio"):
                    note_type = "오디오"
                elif row['mime_type'] and row['mime_type'].startswith("image/"):
                    note_type = "이미지"
                notes_tree.insert("", tk.END, values=(row['title'], row['created_at_kst'], row['modified_at_kst'], note_type), tags=(row['uuid'], row['mime_type'] if 'mime_type' in row else None))

    def show_note_detail(event):
        selected_item = notes_tree.selection()
        if selected_item:
            uuid, mime_type = notes_tree.item(selected_item[0], 'tags')
            note_detail = notes_analyser.get_note_detail(uuid)
            if note_detail:
                note_text.config(state="normal")
                note_text.delete("1.0", tk.END)
                note_text.insert(tk.END, f"제목: {note_detail['제목']}\n")
                note_text.insert(tk.END, f"내용:{note_detail['내용 미리보기']}\n")
                note_text.insert(tk.END, f"UUID: {note_detail['식별자(노트 ID)']}\n")
                note_text.insert(tk.END, f"생성 시간: {note_detail['생성일']}\n")
                note_text.insert(tk.END, f"수정 시간: {note_detail['수정일']}\n")
                note_text.insert(tk.END, f"계정명: {note_detail['계정명']}\n")
                note_text.insert(tk.END, f"마지막 열람: {note_detail['마지막 열람']}\n")
                note_text.insert(tk.END, f"속성 확인 시점: {note_detail['속성 확인 시점']}\n")
                note_text.insert(tk.END, f"최근 업데이트 열람: {note_detail['최근 업데이트 열람']}\n")
                note_text.insert(tk.END, f"요약 열람 시점: {note_detail['요약 열람 시점']}\n")
                note_text.insert(tk.END, f"노트 보기 시점: {note_detail['노트 보기 시점']}\n")
                note_text.insert(tk.END, f"상위폴더 변경일: {note_detail['상위폴더 변경일']}\n")
                note_text.config(state="disabled")

                # 미디어 재생 정보를 저장
                play_media_button.config(state=tk.NORMAL)
                play_media_button.uuid = note_detail['식별자(노트 ID)']
                play_media_button.mime_type = mime_type
                play_media_button.filename = note_detail.get('filename', None)
            else:
                play_media_button.config(state=tk.DISABLED)
        else:
            play_media_button.config(state=tk.DISABLED)


    def find_media_file(uuid: str, filename: str, backup_path: str) -> str | None:
        """
        Manifest.db를 조회하여 UUID와 filename으로 미디어 파일 실제 경로를 찾는다.
        """
        import sqlite3
        from pathlib import Path

        manifest_path = Path(backup_path) / "Manifest.db"
        if not manifest_path.exists():
            print("[오류] Manifest.db가 존재하지 않습니다.")
            return None

        try:
            conn = sqlite3.connect(str(manifest_path))
            cur = conn.cursor()
            # UUID와 filename이 모두 포함된 경로를 찾음
            query = """
                SELECT fileID, relativePath FROM Files
                WHERE domain = 'AppDomainGroup-group.com.apple.notes'
                AND relativePath LIKE ?
            """
            like_pattern = f"%{uuid}%{filename}%"
            cur.execute(query, (like_pattern,))
            result = cur.fetchone()
            conn.close()

            if result:
                file_id, relative_path = result
                file_path = Path(backup_path) / file_id[:2] / file_id
                if file_path.exists():
                    return str(file_path)
                else:
                    print(f"[경고] 파일ID 경로가 존재하지 않음: {file_path}")
            else:
                print(f"[경고] Manifest.db에서 uuid+filename 쿼리 결과 없음: {uuid} / {filename}")
        except Exception as e:
            print(f"[예외] Manifest.db 조회 중 오류: {e}")
        return None




    def play_media():
        uuid = play_media_button.uuid
        mime_type = play_media_button.mime_type
        filename = getattr(play_media_button, "filename", None)

        # mime_type이 없고 filename이 있을 때만 확장자 추정 시도
        if (not mime_type or mime_type == "None") and filename:
            ext = Path(filename).suffix.lower()
            if ext == ".mov":
                mime_type = "video/quicktime"
            elif ext == ".m4a":
                mime_type = "audio/mp4"
            elif ext == ".png":
                mime_type = "image/png"
            else:
                mime_type = "application/octet-stream"

            print(f"[디버그] 확장자로 추정한 MIME: {mime_type}")

        print(f"[디버그] 선택된 UUID: {uuid}")
        print(f"[디버그] 선택된 파일명: {filename}")
        print(f"[디버그] MIME 타입: {mime_type}")

        if uuid and filename:
            media_file_path = find_media_file(uuid, filename, backup_path)
            print(f"[디버그] 매핑된 미디어 경로: {media_file_path}")
            if media_file_path and os.path.exists(media_file_path):
                MediaWindow(content_frame, media_file_path, mime_type)
            else:
                messagebox.showinfo("알림", "해당 노트와 연결된 미디어 파일을 찾을 수 없습니다.")
        else:
            messagebox.showerror("오류", "선택된 노트가 없습니다.")


    # 미디어 재생 버튼
    media_button_frame = ttk.Frame(detail_frame)
    media_button_frame.pack(fill="x", pady=(10, 0), anchor="w")

    play_media_button = ttk.Button(media_button_frame, text="▶️ 미디어 재생", command=play_media, state=tk.DISABLED)
    play_media_button.pack(side="left")
    play_media_button.uuid = None
    play_media_button.mime_type = None
    


    # 초기 노트 목록 로딩
    populate_notes_list()

    # 노트 선택 시 상세 내용 표시 및 미디어 버튼 활성화
    notes_tree.bind("<<TreeviewSelect>>", show_note_detail)

    # UI 스타일 설정 (필요한 경우)
    style = ttk.Style()
    style.configure("Bold.TLabel", font=("default", 12, "bold"))

if __name__ == "__main__":
    # standalone 실행 테스트 (실제 main에서는 사용되지 않음)
    root = tk.Tk()
    root.title("노트 뷰어")
    content_frame = ttk.Frame(root)
    content_frame.pack(fill="both", expand=True, padx=10, pady=10)
    backup_path = "/path/to/your/iOS_Backup"  # 실제 백업 경로로 변경
    display_notes(content_frame, backup_path)
    root.mainloop()