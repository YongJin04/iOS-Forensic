import tkinter as tk
from tkinter import ttk
import sys
import os
from PIL import Image, ImageTk

from gui.styles import apply_styles
from gui.components.display_backup_tree import create_backup_tree_frame
from gui.components.display_file_list import create_file_list_frame
from gui.components.artifact_panel import create_artifact_analysis_options
from gui.components.display_device_info import *
from gui.components.toggle import *

from gui.utils.events import (
    browse_backup_path,
    toggle_password_entry,
    update_file_list_from_backup_tree_click,
    update_backup_tree_from_file_list_double_click
)
from gui.utils.load_backup import load_backup

def start_gui():
    """GUI 애플리케이션을 초기화하고 시작합니다."""
    rootWindow = tk.Tk()
    rootWindow.title("iOS Forensic Viewer")
    
    if sys.platform.startswith('win'):
        from ctypes import windll
        try:
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    
    # 스타일 적용 및 색상 가져오기
    colors = apply_styles(rootWindow)
    
    rootWindow.minsize(1200, 800)
    rootWindow.geometry("1200x800")
    rootWindow.configure(bg=colors['bg_light'])
    
    try:
        from PIL import Image, ImageTk
        icon_path = os.path.join(os.path.dirname(__file__), "icon", "pay1oad.png")
        if os.path.exists(icon_path):
            icon = Image.open(icon_path)
            icon = icon.resize((64, 64))
            icon_image = ImageTk.PhotoImage(icon)
            rootWindow.iconphoto(True, icon_image)
    except Exception:
        pass
        
    setup_gui(rootWindow, colors)
    rootWindow.mainloop()

def setup_gui(rootWindow, colors):
    main_frame = ttk.Frame(rootWindow)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    backup_path_var = tk.StringVar()
    enable_pw_var = tk.IntVar(value=0)
    password_var = tk.StringVar()
    
    control_frame = ttk.Frame(main_frame)
    control_frame.pack(fill="x", padx=10, pady=5)
    control_frame.columnconfigure(0, weight=1)
    control_frame.columnconfigure(1, weight=1)
    uniform_height = 65

    load_frame = ttk.Frame(control_frame, style="Card.TFrame", padding=10, height=uniform_height)
    load_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    load_frame.pack_propagate(False)
    load_grid = ttk.Frame(load_frame)
    load_grid.pack(fill="x", expand=True)
    load_grid.columnconfigure(1, weight=1)
    
    ttk.Label(load_grid, text="Backup Path:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    path_entry = ttk.Entry(load_grid, textvariable=backup_path_var)
    path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    
    btn_frame = ttk.Frame(load_grid)
    btn_frame.grid(row=0, column=2, padx=5, pady=5, sticky="e")
    
    browse_button = ttk.Button(btn_frame, text="Browse", width=10)
    browse_button.pack(side="left", padx=2)
    
    load_backup_button = ttk.Button(btn_frame, text="Load", style="Accent.TButton", width=12)
    load_backup_button.pack(side="left", padx=2)
    
    pw_frame = ttk.Frame(control_frame, style="Card.TFrame", padding=10, height=uniform_height)
    pw_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    pw_frame.pack_propagate(False)

    pw_grid = ttk.Frame(pw_frame)
    pw_grid.pack(fill="x", expand=True)
    
    enable_pw_check = ttk.Checkbutton(pw_grid, text="Encrypted", variable=enable_pw_var)
    enable_pw_check.pack(side="left", padx=5)
    
    ttk.Label(pw_grid, text="Password:").pack(side="left", padx=(10, 5))
    password_entry = ttk.Entry(pw_grid, textvariable=password_var, show="*", state="disabled", style="TEntry")
    password_entry.pack(side="left", fill="x", expand=True, padx=5)
    
    pw_toggle_btn = ttk.Button(pw_grid, text="👁", width=3, style="Icon.TButton")
    pw_toggle_btn.pack(side="right", padx=5)
    
    enable_pw_check.configure(
        command=lambda: toggle_password_entry(enable_pw_var, password_entry, password_var)
    )
    
    backup_loaded_flag = {"loaded": False}

    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Artifact Analysis, Evidence 탭에 새 스타일("Tab.TFrame") 적용
    explorer_tab = ttk.Frame(notebook, padding=5, style="Tab.TFrame")
    notebook.add(explorer_tab, text="  Evidence  ")
    
    paned = ttk.PanedWindow(explorer_tab, orient="horizontal")
    paned.pack(fill="both", expand=True)
    
    backup_tree_widgets = create_backup_tree_frame(paned, colors)
    paned.add(backup_tree_widgets['backup_tree_frame'], weight=3)

    backup_tree = backup_tree_widgets['backup_tree']
    icon_dict = backup_tree_widgets['icon_dict']
    
    file_list_widgets = create_file_list_frame(paned, colors)
    paned.add(file_list_widgets['file_list_frame'], weight=7)
    
    artifact_tab = ttk.Frame(notebook, padding=5, style="Tab.TFrame")
    notebook.add(artifact_tab, text="  Artifact Analysis  ")
    
    artifact_options = create_artifact_analysis_options(artifact_tab, backup_path_var, colors)
    
    notebook.tab(artifact_tab, state="disabled")
    
    browse_button.configure(
        command=lambda: browse_backup_path(backup_path_var, password_entry, password_var, enable_pw_var)
    )
    
    def on_load_backup():
        load_backup(
            backup_path_var.get(),
            password_var.get(),
            backup_tree_widgets['backup_tree'],
            enable_pw_var,
            file_list_widgets['file_list_tree'],
            icon_dict=backup_tree_widgets['icon_dict'],
            flag_container=backup_loaded_flag
        )
        if backup_loaded_flag.get("loaded", False):
            notebook.tab(artifact_tab, state="normal")
    
    load_backup_button.configure(command=on_load_backup)
    
    backup_tree_widgets['backup_tree'].bind(
        "<<TreeviewSelect>>",
        lambda event: update_file_list_from_backup_tree_click(
            event,
            file_list_widgets['file_list_tree'],
            backup_tree_widgets['backup_tree']
        )
    )
    
    file_list_widgets['file_list_tree'].bind(
        "<Double-Button-1>",
        lambda event: update_backup_tree_from_file_list_double_click(
            event,
            file_list_widgets['file_list_tree'],
            backup_tree_widgets['backup_tree']
        )
    )
    
    pw_toggle_var = tk.BooleanVar(value=False)
    pw_toggle_btn.configure(
        command=lambda: toggle_password_visibility(password_entry, pw_toggle_var, pw_toggle_btn)
    )

    return {
        'backup_tree': backup_tree,
        'icon_dict': icon_dict,
    }

def toggle_password_visibility(password_entry, toggle_var, toggle_btn):
    current_state = toggle_var.get()
    if current_state:
        password_entry.config(show="*")
        toggle_btn.config(text="👁")
    else:
        password_entry.config(show="")
        toggle_btn.config(text="")
    toggle_var.set(not current_state)
