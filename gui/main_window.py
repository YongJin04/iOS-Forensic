import tkinter as tk
from tkinter import ttk
import os
import sys

from gui.gui_layout import setup_gui

if sys.platform == "win32":
    import ctypes

def start_gui():
    """ GUI 실행 함수 """
    root = tk.Tk()
    root.title("iOS Forensic Viewer")

    # Windows 작업 표시줄 아이콘 설정 (예시)
    icon_path_ico = os.path.abspath(os.path.join("gui", "icon", "pay1oad.ico"))
    if sys.platform == "win32":
        if os.path.exists(icon_path_ico):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("iOS.Forensic.Viewer")
            root.iconbitmap(icon_path_ico)

    # 최소 크기 제한
    root.minsize(650, 400)
    # 창 크기 초기 설정
    root.geometry("900x600")

    # 레이아웃 세팅
    setup_gui(root)

    root.mainloop()

if __name__ == "__main__":
    start_gui()
