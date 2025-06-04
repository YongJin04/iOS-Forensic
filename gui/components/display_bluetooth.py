from tkinter import ttk, messagebox
import tkinter as tk
import sqlite3
from pathlib import Path

def clean_address(address: str) -> str:
    if isinstance(address, str):
        parts = address.strip().split()
        return parts[-1] if parts else address
    return address

def fetch_bluetooth_devices(backup_path: str):
    """OtherDevices → (uuid, name, mac, last_seen_raw)"""
    db_path = Path(backup_path) / "3a/3afe56e2c5aa8c090ded49445d95e8769ef34899"
    if not db_path.exists():
        return []

    results = []
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT Uuid, Name, Address, LastSeenTime FROM OtherDevices")
            for uuid, name, addr, last in cur.fetchall():
                results.append(
                    (
                        uuid,
                        name or "",
                        clean_address(addr),
                        last if last is not None else "Unknown",
                    )
                )
    except Exception as e:
        results.append(("Error", str(e), "", ""))
    return results

def display_bluetooth(content_frame, backup_path: str):
    # ---------- 레이아웃 초기화 ----------
    for w in content_frame.winfo_children():
        w.destroy()

    root = ttk.Frame(content_frame)
    root.pack(fill="both", expand=True)

    ttk.Label(
        root, text="🔵 Paired Bluetooth Devices", style="CardHeader.TLabel"
    ).pack(anchor="w", pady=(0, 6))

    # ---------- 검색 바 ----------
    top = ttk.Frame(root)
    top.pack(fill="x", pady=(0, 6))
    ttk.Label(top, text="Search:").pack(side="left")
    key = tk.StringVar()
    ent = ttk.Entry(top, textvariable=key, width=40)
    ent.pack(side="left", padx=4)
    btn = ttk.Button(top, text="Search")
    btn.pack(side="left", padx=4)

    # ---------- 테이블 ----------
    table = ttk.Frame(root)
    table.pack(fill="both", expand=True)

    cols = ("uuid", "name", "addr", "seen")
    tree = ttk.Treeview(table, columns=cols, show="headings")

    # 헤더
    tree.heading("uuid", text="UUID")
    tree.heading("name", text="Device Name")
    tree.heading("addr", text="MAC Address")
    tree.heading("seen", text="Last Seen")

    # 모든 컬럼에 동일한 width와 stretch=True 적용 (균등 분배)
    for col in cols:
        tree.column(col, width=100, stretch=True)

    tree.tag_configure("stripe", background="#f5f5f5")

    vsb = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(table, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    table.rowconfigure(0, weight=1)
    table.columnconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    # ---------- 데이터 로드 ----------
    data = fetch_bluetooth_devices(backup_path)
    data.sort(key=lambda x: (not x[1], x[1]))

    def populate(rows):
        tree.delete(*tree.get_children())
        for i, r in enumerate(rows):
            tag = ("stripe",) if i % 2 else ()
            tree.insert("", "end", values=r, tags=tag)

    # ---------- 검색 ----------
    def do_search(_e=None):
        kw = key.get().lower()
        if not kw:
            populate(data)
            return
        populate(
            [
                r
                for r in data
                if any(kw in str(cell).lower() for cell in r)
            ]
        )

    btn.configure(command=do_search)
    ent.bind("<Return>", do_search)

    populate(data)

    # 휠 스크롤
    tree.bind(
        "<MouseWheel>",
        lambda e: tree.yview_scroll(int(-1 * (e.delta / 120)), "units"),
    )
