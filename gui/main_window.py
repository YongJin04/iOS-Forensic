# main_window.py
import tkinter as tk
from tkinter import ttk
import os
import sys

from gui.gui_layout import setup_gui

# Windows에서 작업 표시줄 아이콘을 변경하기 위한 모듈
if sys.platform == "win32":
    import ctypes

def start_gui():
    """ GUI 실행 함수 (반응형 적용 + 작업 표시줄 아이콘 변경) """
    root = tk.Tk()
    root.title("iOS Forensic Viewer")

    # 아이콘 경로 설정
    icon_path_ico = os.path.abspath(os.path.join("gui", "icon", "pay1oad.ico"))

    # Windows 작업 표시줄 아이콘 설정
    if sys.platform == "win32":
        if os.path.exists(icon_path_ico):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("iOS.Forensic.Viewer")
            root.iconbitmap(icon_path_ico)

    # 최소 크기 제한 (너무 작아지지 않도록)
    root.minsize(650, 400)

    # 전체 화면 크기 조정 가능
    root.geometry("900x600")

    # 창 크기 조정 시, 내부 요소도 자동 확장되도록 설정
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    setup_gui(root)

    root.mainloop()

if __name__ == "__main__":
    start_gui()
