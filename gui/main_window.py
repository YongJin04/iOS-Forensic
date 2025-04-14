# main_window.py
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
from gui.utils.load_backup import load_backup
from gui.components.display_preview import PreviewManager
from gui.utils.events import *

def start_gui() -> None:
    """GUI 애플리케이션을 초기화하고 시작합니다."""
    rootWindow = tk.Tk()
    rootWindow.title("iOS Forensic Viewer")

    # Windows DPI 스케일링
    if sys.platform.startswith("win"):
        from ctypes import windll

        try:
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    # 스타일 및 색상
    colors = apply_styles(rootWindow)

    rootWindow.minsize(1200, 800)
    rootWindow.geometry("1200x800")
    rootWindow.configure(bg=colors["bg_light"])

    # 앱 아이콘
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "icon", "pay1oad.png")
        if os.path.exists(icon_path):
            icon = Image.open(icon_path).resize((64, 64))
            rootWindow.iconphoto(True, ImageTk.PhotoImage(icon))
    except Exception:
        pass

    setup_gui(rootWindow, colors)
    rootWindow.mainloop()


def setup_gui(rootWindow: tk.Tk, colors: dict[str, str]) -> dict:
    """GUI 레이아웃을 구성합니다."""
    # ─── 컨테이너 ───────────────────────────────────────────────
    main_frame = ttk.Frame(rootWindow)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # ─── 변수 ───────────────────────────────────────────────────
    backup_path_var = tk.StringVar()
    enable_pw_var = tk.IntVar(value=0)
    password_var = tk.StringVar()
    backup_loaded_flag: dict[str, bool] = {"loaded": False}

    # ─── 상단 제어 영역 ────────────────────────────────────────
    control_frame = ttk.Frame(main_frame)
    control_frame.pack(fill="x", padx=10, pady=5)
    control_frame.columnconfigure((0, 1), weight=1)
    uniform_height = 65

    # --- 백업 로드 프레임 --------------------------------------
    load_frame = ttk.Frame(
        control_frame, style="Card.TFrame", padding=10, height=uniform_height
    )
    load_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    load_frame.pack_propagate(False)

    load_grid = ttk.Frame(load_frame)
    load_grid.pack(fill="x", expand=True)
    load_grid.columnconfigure(1, weight=1)

    ttk.Label(load_grid, text="Backup Path:").grid(
        row=0, column=0, padx=5, pady=5, sticky="w"
    )
    path_entry = ttk.Entry(load_grid, textvariable=backup_path_var)
    path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    btn_frame = ttk.Frame(load_grid)
    btn_frame.grid(row=0, column=2, padx=5, pady=5, sticky="e")

    browse_button = ttk.Button(btn_frame, text="Browse", width=10)
    browse_button.pack(side="left", padx=2)

    load_backup_button = ttk.Button(btn_frame, text="Load", style="Accent.TButton", width=12)
    load_backup_button.pack(side="left", padx=2)

    # --- 비밀번호 프레임 ---------------------------------------
    pw_frame = ttk.Frame(
        control_frame, style="Card.TFrame", padding=10, height=uniform_height
    )
    pw_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    pw_frame.pack_propagate(False)

    pw_grid = ttk.Frame(pw_frame)
    pw_grid.pack(fill="x", expand=True)

    enable_pw_check = ttk.Checkbutton(pw_grid, text="Encrypted", variable=enable_pw_var)
    enable_pw_check.pack(side="left", padx=5)

    ttk.Label(pw_grid, text="Password:").pack(side="left", padx=(10, 5))
    password_entry = ttk.Entry(
        pw_grid, textvariable=password_var, show="*", state="disabled", style="TEntry"
    )
    password_entry.pack(side="left", fill="x", expand=True, padx=5)

    pw_toggle_btn = ttk.Button(pw_grid, text="👁", width=3, style="Icon.TButton")
    pw_toggle_btn.pack(side="right", padx=5)

    enable_pw_check.configure(
        command=lambda: toggle_password_entry(enable_pw_var, password_entry, password_var)
    )

    # ─── 노트북(탭) ─────────────────────────────────────────────
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # --- Evidence(탐색) 탭 -------------------------------------
    explorer_tab = ttk.Frame(notebook, padding=5)
    notebook.add(explorer_tab, text="  Evidence  ")

    paned = ttk.PanedWindow(explorer_tab, orient="horizontal")
    paned.pack(fill="both", expand=True)

    backup_tree_widgets = create_backup_tree_frame(paned, colors)
    paned.add(backup_tree_widgets["backup_tree_frame"], weight=3)

    backup_tree = backup_tree_widgets["backup_tree"]
    icon_dict = backup_tree_widgets["icon_dict"]

    file_list_widgets = create_file_list_frame(paned, colors)
    paned.add(file_list_widgets["file_list_frame"], weight=7)

    # --- Artifact Analysis 탭 ----------------------------------
    artifact_tab = ttk.Frame(notebook, padding=5)
    notebook.add(artifact_tab, text="  Artifact Analysis  ")
    create_artifact_analysis_options(artifact_tab, backup_path_var, colors)
    notebook.tab(artifact_tab, state="disabled")  # 처음엔 비활성화

    # ─── PreviewManager 연결 (NEW) ─────────────────────────────
    preview_manager = PreviewManager(
        preview_label=file_list_widgets["preview_label"],
        file_list_tree=file_list_widgets["file_list_tree"],
        backup_path_var=backup_path_var,
    )
    # 가비지 컬렉션 방지용 참조
    file_list_widgets["preview_manager"] = preview_manager
    # ───────────────────────────────────────────────────────────

    # ─── 이벤트 바인딩 ─────────────────────────────────────────
    browse_button.configure(
        command=lambda: browse_backup_path(
            backup_path_var, password_entry, password_var, enable_pw_var
        )
    )

    def on_load_backup():
        load_backup(
            backup_path_var.get(),
            password_var.get(),
            backup_tree,
            enable_pw_var,
            file_list_widgets["file_list_tree"],
            icon_dict=icon_dict,
            flag_container=backup_loaded_flag,
        )
        # 백업이 성공적으로 로드되면 Artifact 탭 활성화
        if backup_loaded_flag.get("loaded"):
            notebook.tab(artifact_tab, state="normal")

    load_backup_button.configure(command=on_load_backup)

    backup_tree.bind(
        "<<TreeviewSelect>>",
        lambda event: update_file_list_from_backup_tree_click(
            event,
            file_list_widgets["file_list_tree"],
            backup_tree,
            backup_path_var.get(),
        ),
    )

    file_list_widgets["file_list_tree"].bind(
        "<Double-Button-1>",
        lambda event: update_backup_tree_from_file_list_double_click(
            event,
            file_list_widgets["file_list_tree"],
            backup_tree,
        ),
    )

    file_list_widgets["file_list_tree"].bind(
        "<Button-3>",
        lambda event: show_file_paths(
            event,
            file_list_widgets["file_list_tree"],
            backup_path_var.get(),
        ),
    )

    # 비밀번호 표시/숨김 토글
    pw_toggle_var = tk.BooleanVar(value=False)
    pw_toggle_btn.configure(
        command=lambda: toggle_password_visibility(
            password_entry, pw_toggle_var, pw_toggle_btn
        )
    )

    return {"backup_tree": backup_tree, "icon_dict": icon_dict}


def toggle_password_visibility(
    password_entry: ttk.Entry, toggle_var: tk.BooleanVar, toggle_btn: ttk.Button
) -> None:
    """비밀번호 표시/숨김을 전환합니다."""
    if toggle_var.get():
        password_entry.config(show="*")
        toggle_btn.config(text="👁")
    else:
        password_entry.config(show="")
        toggle_btn.config(text="")
    toggle_var.set(not toggle_var.get())
