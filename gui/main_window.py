import tkinter as tk
from tkinter import ttk
from gui.gui_utils import setup_gui

def start_gui():
    """ GUI 실행 함수 """
    root = tk.Tk()
    root.title("iTunes Backup Viewer")
    root.geometry("700x500")

    setup_gui(root)

    root.mainloop()

if __name__ == "__main__":
    start_gui()
