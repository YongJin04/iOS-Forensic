from tkinter import ttk, messagebox
import tkinter as tk
from artifact_analyzer.call.call_history import CallHistoryAnalyzer


def display_call_history(parent_frame, backup_path: str):
    # 기존 위젯 제거
    for w in parent_frame.winfo_children():
        w.destroy()

    analyzer = CallHistoryAnalyzer(backup_path)
    ok, msg = analyzer.load_call_records()
    if not ok:
        messagebox.showerror("오류", msg)
        return

    # ── 레이아웃 ──────────────────────────────
    root = ttk.Frame(parent_frame, padding=10)
    root.pack(fill="both", expand=True)

    # 검색 바
    bar = ttk.Frame(root)
    bar.pack(fill="x")
    ttk.Label(bar, text="검색:").pack(side="left")
    kw_var = tk.StringVar()
    ent = ttk.Entry(bar, textvariable=kw_var, width=40)
    ent.pack(side="left", padx=5)
    btn = ttk.Button(bar, text="검색")
    btn.pack(side="left", padx=5)

    # ── 트리뷰 ────────────────────────────────
    tree_fr = ttk.Frame(root)
    tree_fr.pack(fill="both", expand=True, pady=10)

    cols = ("phone", "name", "dir", "date", "dur", "svc")
    tree = ttk.Treeview(tree_fr, columns=cols, show="headings", height=25)

    tree.heading("phone", text="PhoneNumber")
    tree.heading("name",  text="Name")
    tree.heading("dir",   text="Direction")
    tree.heading("date",  text="CallStartTime")
    tree.heading("dur",   text="PurificationTime")
    tree.heading("svc",   text="Service")

    tree.column("phone", width=140)
    tree.column("name",  width=160)
    tree.column("dir",   width=90,  anchor="center")
    tree.column("date",  width=200)
    tree.column("dur",   width=120, anchor="center")
    tree.column("svc",   width=90,  anchor="center")

    tree.tag_configure("stripe", background="#f5f5f5")

    vsb = ttk.Scrollbar(tree_fr, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    # ── 데이터 로드 ────────────────────────────
    def populate(records):
        tree.delete(*tree.get_children())
        for i, r in enumerate(records):
            tag = ("stripe",) if i % 2 else ()
            tree.insert(
                "", "end",
                iid=str(r.z_pk),      # ID는 내부 참조용으로만 사용
                values=(
                    r.phone_number,
                    r.zname,
                    r.direction,       # Incoming / Outgoing
                    r.date_str,
                    r.duration_str,
                    r.service,
                ),
                tags=tag
            )

    def do_search(_e=None):
        populate(analyzer.search(kw_var.get().strip()))

    btn.configure(command=do_search)
    ent.bind("<Return>", do_search)

    populate(analyzer.call_records)
