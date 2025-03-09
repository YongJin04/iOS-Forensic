# gui_layout.py

import tkinter as tk
from tkinter import ttk
from gui.gui_events import (
    browse_backup_path, 
    toggle_password_entry, 
    on_backup_tree_select, 
    on_file_list_tree_open,
    on_file_list_double_click
)
from gui.load_backup_utils import load_backup

def setup_gui(root):
    """ GUI 레이아웃 설정 """
    frame = ttk.Frame(root, padding=15)
    frame.pack(fill="both", expand=True)

    backup_path_var = tk.StringVar()
    password_var = tk.StringVar()
    enable_pw_var = tk.IntVar(value=0)

    # Backup Directory + Load Backup
    top_frame = ttk.Frame(frame)
    top_frame.pack(fill="x", pady=5)

    ttk.Label(top_frame, text="Backup Directory:", font=("Helvetica", 10)).pack(side="left", padx=5)
    path_entry = ttk.Entry(top_frame, textvariable=backup_path_var, width=40)
    path_entry.pack(side="left", padx=5)
    ttk.Button(
        top_frame, 
        text="Browse", 
        command=lambda: browse_backup_path(backup_path_var, password_entry, password_var, enable_pw_var)
    ).pack(side="left", padx=5)

    ttk.Button(
        top_frame, 
        text="Load Backup", 
        command=lambda: load_backup(backup_path_var.get(), password_var.get(), tree_widget, enable_pw_var, file_list_tree),
        style="large.TButton"
    ).pack(side="right", padx=10)

    # Password + Enable Password
    pw_frame = ttk.Frame(frame)
    pw_frame.pack(fill="x", pady=5)

    enable_pw_check = ttk.Checkbutton(
        pw_frame, 
        text="Enable Password", 
        variable=enable_pw_var,
        command=lambda: toggle_password_entry(enable_pw_var, password_entry, password_var)
    )
    enable_pw_check.pack(side="left", padx=5)

    ttk.Label(pw_frame, text="Password:", font=("Helvetica", 10)).pack(side="left", padx=5)
    password_entry = ttk.Entry(pw_frame, textvariable=password_var, width=30, show="*")
    password_entry.pack(side="left", padx=5)
    password_entry.config(state="disabled")  # 초기 상태는 비활성화

    # PanedWindow (왼쪽: Tree, 오른쪽: File List)
    paned = ttk.PanedWindow(frame, orient="horizontal")
    paned.pack(fill="both", expand=True, pady=10)

    # -------------------------------
    # 왼쪽 영역: Backup Tree
    # -------------------------------
    tree_frame = ttk.Frame(paned)
    tree_widget = ttk.Treeview(tree_frame)
    tree_widget.heading("#0", text="Backup Tree", anchor="w")
    tree_widget.pack(side="left", fill="both", expand=True)

    tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree_widget.yview)
    tree_scrollbar.pack(side="right", fill="y")
    tree_widget.configure(yscrollcommand=tree_scrollbar.set)

    paned.add(tree_frame, weight=1)

    # -------------------------------
    # 오른쪽 영역: File List (TreeView)
    # -------------------------------
    file_list_frame = ttk.Frame(paned)
    # ---- [수정] 기존에 별도 Label을 두었던 부분 제거 ----
    # ttk.Label(file_list_frame, text="File List", font=("Helvetica", 10)).pack(anchor="w", padx=5, pady=2)

    file_list_tree = ttk.Treeview(file_list_frame)
    # ---- [수정] 트리뷰 자체 헤더를 "File List"로 변경 ----
    file_list_tree.heading("#0", text="File List", anchor="w")
    file_list_tree.pack(side="left", fill="both", expand=True)

    file_list_scrollbar = ttk.Scrollbar(file_list_frame, orient="vertical", command=file_list_tree.yview)
    file_list_scrollbar.pack(side="right", fill="y")
    file_list_tree.configure(yscrollcommand=file_list_scrollbar.set)

    paned.add(file_list_frame, weight=1)

    # 이벤트 바인딩
    # Backup Tree에서 노드 선택 시 File List 갱신
    tree_widget.bind("<<TreeviewSelect>>", lambda event: on_backup_tree_select(event, file_list_tree, tree_widget))

    # File List Tree에서 디렉토리 열 때 (토글)
    file_list_tree.bind("<<TreeviewOpen>>", lambda event: on_file_list_tree_open(event, file_list_tree, tree_widget))

    # File List Tree에서 디렉토리 더블클릭 시
    file_list_tree.bind("<Double-Button-1>", lambda event: on_file_list_double_click(event, file_list_tree, tree_widget))
