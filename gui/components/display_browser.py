import tkinter as tk
from tkinter import ttk

def display_browser(content_frame, backup_path):
    # 기존 위젯 삭제
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    # 헤더 추가
    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill="x", pady=(0, 10))
    
    ttk.Label(header_frame, text="🌐 브라우저", style="ContentHeader.TLabel").pack(side="left")
    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))
    
    # 메시지 카드
    browser_card = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
    browser_card.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 메시지 앱 선택 영역
    browser_select_frame = ttk.Frame(browser_card)
    browser_select_frame.pack(fill="x", pady=(0, 15))
    
    ttk.Label(browser_select_frame, text="브라우저:", style="InfoLabel.TLabel").pack(side="left", padx=(0, 5))
    
    app_var = tk.StringVar(value="기본 메시지")
    app_combo = ttk.Combobox(browser_select_frame, textvariable=app_var, values=["Chrome", "Safari", "기타"])
    app_combo.pack(side="left", padx=(0, 10))
    
    ttk.Button(browser_select_frame, text="조회", style="AccentButton.TButton", width=8).pack(side="left")
    
    # 메시지 표시 영역
    message_paned = ttk.PanedWindow(browser_card, orient="horizontal")
    message_paned.pack(fill="both", expand=True, pady=(10, 0))
    
