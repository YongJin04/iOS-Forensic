from tkinter import ttk
import tkinter as tk
import os
import biplist

def display_wifi(content_frame, backup_path):
    for widget in content_frame.winfo_children():
        widget.destroy()

    frame = ttk.Frame(content_frame, style="Card.TFrame", padding=20)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(frame, text="📶 Wi-Fi 분석 (테이블 보기)", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))

    table_frame = ttk.Frame(frame)
    table_frame.pack(fill="both", expand=True)

    # 스크롤바
    scrollbar = ttk.Scrollbar(table_frame)
    scrollbar.pack(side="right", fill="y")

    # 테이블 (TreeView)
    tree = ttk.Treeview(table_frame, columns=("ssid", "mac", "lastjoined", "addedat"), show="headings", yscrollcommand=scrollbar.set)
    tree.pack(fill="both", expand=True)
    scrollbar.config(command=tree.yview)

    # 컬럼 정의
    tree.heading("ssid", text="SSID_STR")
    tree.heading("mac", text="MAC_Address")
    tree.heading("lastjoined", text="Last Joined")
    tree.heading("addedat", text="Added At")

    tree.column("ssid", width=180, anchor="w")
    tree.column("mac", width=180, anchor="w")
    tree.column("lastjoined", width=200, anchor="w")
    tree.column("addedat", width=200, anchor="w")

    # bplist 경로
    plist_path = os.path.join(backup_path, "e3", "e36b35ae4cc6038f9ce83b5e097f216144278b17")

    # 데이터 파싱 및 테이블 삽입
    try:
        if os.path.exists(plist_path):
            plist_data = biplist.readPlist(plist_path)
            network_list = plist_data.get("List of scanned networks with private mac", [])
            
            def format_mac_address(raw_mac):
                if isinstance(raw_mac, bytes) and len(raw_mac) == 6:
                    return ":".join(f"{b:02X}" for b in raw_mac)
                elif isinstance(raw_mac, str):
                    if len(raw_mac) == 12:
                        return ":".join(raw_mac[i:i+2] for i in range(0, 12, 2)).upper()
                    return raw_mac
                return "알 수 없음"

            # 테이블 삽입 부분
            for entry in network_list:
                ssid = entry.get("SSID_STR", "")
                mac_raw = entry.get("PRIVATE_MAC_ADDRESS", {}).get("PRIVATE_MAC_ADDRESS_VALUE", "")
                mac = format_mac_address(mac_raw)
                last_joined = entry.get("lastJoined", "")
                added_at = entry.get("addedAt", "")
                tree.insert("", "end", values=(ssid, mac, str(last_joined), str(added_at)))
        else:
            tree.insert("", "end", values=("파일을 찾을 수 없습니다", "", "", ""))
    except Exception as e:
        tree.insert("", "end", values=(f"오류: {str(e)}", "", "", ""))

    # 마우스 휠 스크롤
    def _on_mouse_wheel(event):
        tree.yview_scroll(int(-1*(event.delta/120)), "units")

    tree.bind("<MouseWheel>", _on_mouse_wheel)
