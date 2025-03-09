import tkinter as tk
from tkinter import ttk
from gui.gui_layout import setup_gui

def start_gui():
    """ GUI 실행 함수 (반응형 적용) """
    root = tk.Tk()
    root.title("iTunes Backup Viewer")

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
