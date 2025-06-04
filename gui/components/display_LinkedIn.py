import tkinter as tk
from tkinter import ttk, messagebox
import plistlib
from pathlib import Path

def fetch_linkedin_info(backup_path: str):
    """LinkedIn 관련 정보 추출 (이름 매핑 포함)"""
    from plistlib import load, FMT_BINARY

    file_path = Path(backup_path) / "9c/9c404eb0aa691005cdbd1e97ca74685c334f3635"
    if not file_path.exists():
        return [("Error", "파일이 존재하지 않음")]

    try:
        with open(file_path, "rb") as f:
            data = load(f, fmt=FMT_BINARY)
    except Exception as e:
        return [("Error", f"파싱 실패: {e}")]

    # 대상 경로와 UI 표시명을 매핑
    TARGET_PATHS = {
        "voy.authenticatedDashProfileModel.lastName": "Name",
        "voy.authenticatedDashProfileModel.firstName": "Organization",
        "voy.authenticatedDashProfileModel.geoLocation.geo.defaultLocalizedName": "ResidenceName",
    }

    results = []

    def recursive_search(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_path = f"{path}.{k}" if path else k
                recursive_search(v, full_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                recursive_search(item, f"{path}[{i}]")
        else:
            if path in TARGET_PATHS:
                label = TARGET_PATHS[path]
                results.append((label, str(obj)))

    recursive_search(data)

    if not results:
        results.append(("Info", "❗️ 대상 키를 찾을 수 없습니다."))

    return results


def display_LinkedIn(content_frame, backup_path: str):
    for w in content_frame.winfo_children():
        w.destroy()

    root = ttk.Frame(content_frame)
    root.pack(fill="both", expand=True)

    ttk.Label(root, text="💼 LinkedIn Profile Info", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 6))

    table = ttk.Frame(root)
    table.pack(fill="both", expand=True)

    cols = ("key", "value")
    tree = ttk.Treeview(table, columns=cols, show="headings")

    tree.heading("key", text="Field")
    tree.heading("value", text="Value")

    tree.column("key", width=160, stretch=False)
    tree.column("value", width=400, stretch=True)

    tree.tag_configure("stripe", background="#f5f5f5")

    vsb = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(table, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    table.rowconfigure(0, weight=1)
    table.columnconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    # 데이터 불러오기 및 UI 반영
    data = fetch_linkedin_info(backup_path)

    def populate(rows):
        tree.delete(*tree.get_children())
        for i, (k, v) in enumerate(rows):
            tag = ("stripe",) if i % 2 else ()
            tree.insert("", "end", values=(k, v), tags=tag)

    populate(data)

    tree.bind("<MouseWheel>", lambda e: tree.yview_scroll(int(-1 * (e.delta / 120)), "units"))
