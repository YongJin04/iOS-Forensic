import tkinter as tk
from tkinter import ttk, messagebox
from artifact_analyzer.addressbook.addressbook_analyzer import ContactContentAnalyzer  

def display_contact_content(parent_frame, backup_path: str):
    # 기존 위젯 제거
    for w in parent_frame.winfo_children():
        w.destroy()

    analyzer = ContactContentAnalyzer(backup_path)
    ok, msg = analyzer.load_contacts()
    if not ok:
        messagebox.showerror("Error", msg)
        return

    # ── 최상위 프레임 ───────────────────────────
    root = ttk.Frame(parent_frame)           # ★ padding 제거
    root.pack(fill="both", expand=True)

    # 검색 바
    bar = ttk.Frame(root)
    bar.pack(fill="x", pady=(0, 6))
    ttk.Label(bar, text="검색:").pack(side="left")
    kw_var = tk.StringVar()
    ent = ttk.Entry(bar, textvariable=kw_var, width=40)
    ent.pack(side="left", padx=4)
    btn = ttk.Button(bar, text="검색")
    btn.pack(side="left", padx=4)

    # ── 트리뷰 컨테이너 ────────────────────────
    table = ttk.Frame(root)                  # ★ 별도 padding 삭제
    table.pack(fill="both", expand=True)

    cols = ("phone", "name", "org", "created", "modified")
    tree = ttk.Treeview(table, columns=cols, show="headings")

    tree.heading("phone",    text="PhoneNumber")
    tree.heading("name",     text="Name")
    tree.heading("org",      text="Organization")
    tree.heading("created",  text="Created")
    tree.heading("modified", text="Modified")

    # ── 열 폭 & Stretch 설정 ──────────────────
    tree.column("phone",    width=140, stretch=False)
    tree.column("name",     width=160, stretch=False)
    tree.column("org",      width=180, stretch=False)
    tree.column("created",  width=150, stretch=False)
    tree.column("modified", width=150, stretch=True)   # ★ 마지막 열이 빈 공간을 흡수

    # 스트라이프
    tree.tag_configure("stripe", background="#f5f5f5")

    # 스크롤바
    vsb = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(table, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # grid 배치
    table.rowconfigure(0, weight=1)
    table.columnconfigure(0, weight=1)  # tree가 가로 공간 전부 차지
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    # ── 데이터 채우기 ──────────────────────────
    def populate(items):
        tree.delete(*tree.get_children())
        for i, c in enumerate(items):
            tag = ("stripe",) if i % 2 else ()
            tree.insert(
                "", "end",
                iid=str(c.rowid),
                values=(c.phone, c.full_name, c.org, c.created, c.modified),
                tags=tag,
            )

    def do_search(_e=None):
        populate(analyzer.search(kw_var.get().strip()))

    btn.configure(command=do_search)
    ent.bind("<Return>", do_search)

    populate(analyzer.contacts)