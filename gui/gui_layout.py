import tkinter as tk
from tkinter import ttk
from gui.gui_events import browse_backup_path, load_backup, toggle_password_entry

def setup_gui(root):
    """ GUI 레이아웃 설정 """
    frame = ttk.Frame(root, padding=15)
    frame.pack(fill="both", expand=True)

    backup_path_var = tk.StringVar()
    password_var = tk.StringVar()
    enable_pw_var = tk.IntVar(value=0)

    # Backup Directory 입력 + Load Backup 버튼 (같은 줄에 배치)
    top_frame = ttk.Frame(frame)
    top_frame.pack(fill="x", pady=5)

    ttk.Label(top_frame, text="Backup Directory:", font=("Helvetica", 10)).pack(side="left", padx=5)
    path_entry = ttk.Entry(top_frame, textvariable=backup_path_var, width=40)
    path_entry.pack(side="left", padx=5)
    ttk.Button(top_frame, text="Browse", command=lambda: browse_backup_path(
        backup_path_var, password_entry, password_var, enable_pw_var)).pack(side="left", padx=5)

    ttk.Button(top_frame, text="Load Backup", command=lambda: load_backup(
        backup_path_var.get(), password_var.get(), tree_widget, enable_pw_var
    ), style="large.TButton").pack(side="right", padx=10)

    # Password 입력 필드 및 Enable Password 체크박스
    pw_frame = ttk.Frame(frame)
    pw_frame.pack(fill="x", pady=5)

    enable_pw_check = ttk.Checkbutton(pw_frame, text="Enable Password", variable=enable_pw_var,
                                      command=lambda: toggle_password_entry(enable_pw_var, password_entry, password_var))
    enable_pw_check.pack(side="left", padx=5)

    ttk.Label(pw_frame, text="Password:", font=("Helvetica", 10)).pack(side="left", padx=5)
    password_entry = ttk.Entry(pw_frame, textvariable=password_var, width=30, show="*")
    password_entry.pack(side="left", padx=5)
    password_entry.config(state="disabled")  # 초기 상태는 비활성화

    # TreeView (파일 트리)
    tree_widget = ttk.Treeview(frame)
    tree_widget.heading("#0", text="Backup File Tree", anchor="w")
    tree_widget.pack(fill="both", expand=True, pady=10)
