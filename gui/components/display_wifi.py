from tkinter import ttk, messagebox
import tkinter as tk
import os
import biplist


def display_wifi(content_frame, backup_path):
    # ── 기존 위젯 정리 ───────────────────────────────────────────
    for w in content_frame.winfo_children():
        w.destroy()

    root = ttk.Frame(content_frame)          # padding X → 여백 최소
    root.pack(fill="both", expand=True)

    # 제목
    ttk.Label(root, text="📶 Wi-Fi 분석 (테이블 보기)",
              style="CardHeader.TLabel").pack(anchor="w", pady=(0, 6))

    # ── 검색 바 ─────────────────────────────────────────────────
    search_bar = ttk.Frame(root)
    search_bar.pack(fill="x", pady=(0, 6))

    ttk.Label(search_bar, text="검색:").pack(side="left")
    kw_var = tk.StringVar()
    ent = ttk.Entry(search_bar, textvariable=kw_var, width=40)
    ent.pack(side="left", padx=4)
    btn = ttk.Button(search_bar, text="검색")
    btn.pack(side="left", padx=4)

    # ── 트리뷰 컨테이너 ───────────────────────────────────────
    table = ttk.Frame(root)
    table.pack(fill="both", expand=True)

    cols = ("ssid", "mac", "lastjoined", "addedat")
    tree = ttk.Treeview(table, columns=cols, show="headings")

    # 헤더
    tree.heading("ssid",        text="SSID_STR")
    tree.heading("mac",         text="MAC_Address")
    tree.heading("lastjoined",  text="Last Joined")
    tree.heading("addedat",     text="Added At")

    # 열 폭 (마지막 열 stretch = True → 남는 폭 흡수)
    tree.column("ssid",        width=180, stretch=False)
    tree.column("mac",         width=180, stretch=False)
    tree.column("lastjoined",  width=200, stretch=False)
    tree.column("addedat",     width=200, stretch=True)

    # 스트라이프 줄무늬
    tree.tag_configure("stripe", background="#f5f5f5")

    # 스크롤바
    vsb = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(table, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # grid 배치 (프레임 안에서 리사이즈)
    table.rowconfigure(0, weight=1)
    table.columnconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    # ── 데이터 파싱 (원본 로직 그대로) ───────────────────────────
    plist_path = os.path.join(
        backup_path, "e3", "e36b35ae4cc6038f9ce83b5e097f216144278b17"
    )

    def format_mac_address(raw_mac):
        if isinstance(raw_mac, bytes) and len(raw_mac) == 6:
            return ":".join(f"{b:02X}" for b in raw_mac)
        if isinstance(raw_mac, str):
            if len(raw_mac) == 12:
                return ":".join(raw_mac[i:i + 2] for i in range(0, 12, 2)).upper()
            return raw_mac
        return "알 수 없음"

    all_rows = []  # 전체 레코드 보관 → 검색용

    try:
        if os.path.exists(plist_path):
            plist_data = biplist.readPlist(plist_path)
            network_list = plist_data.get(
                "List of scanned networks with private mac", []
            )
            for entry in network_list:
                ssid = entry.get("SSID_STR", "")
                mac_raw = entry.get("PRIVATE_MAC_ADDRESS", {}).get(
                    "PRIVATE_MAC_ADDRESS_VALUE", ""
                )
                mac = format_mac_address(mac_raw)
                last_joined = str(entry.get("lastJoined", ""))
                added_at = str(entry.get("addedAt", ""))
                all_rows.append((ssid, mac, last_joined, added_at))
        else:
            all_rows.append(("파일을 찾을 수 없습니다", "", "", ""))
    except Exception as e:
        all_rows.append((f"오류: {e}", "", "", ""))

    # ── 표시 & 검색 ───────────────────────────────────────────
    def populate(rows):
        tree.delete(*tree.get_children())
        for i, row in enumerate(rows):
            tag = ("stripe",) if i % 2 else ()
            tree.insert("", "end", values=row, tags=tag)

    def do_search(_e=None):
        kw = kw_var.get().lower()
        if not kw:
            populate(all_rows)
            return
        filtered = [
            r for r in all_rows
            if any(kw in str(cell).lower() for cell in r)
        ]
        populate(filtered)

    btn.configure(command=do_search)
    ent.bind("<Return>", do_search)

    populate(all_rows)

    # 휠 스크롤 (Windows·mac 공통)
    def _on_mousewheel(event):
        tree.yview_scroll(int(-1 * (event.delta / 120)), "units")

    tree.bind("<MouseWheel>", _on_mousewheel)
