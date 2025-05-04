import tkinter as tk
from tkinter import ttk

def display_messages(content_frame, backup_path):
    """메시지를 콘텐츠 프레임에 표시합니다."""
    # 기존 위젯 삭제
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    # 헤더 추가
    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill="x", pady=(0, 10))
    
    ttk.Label(header_frame, text="💬 메시지", style="ContentHeader.TLabel").pack(side="left")
    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))
    
    # 메시지 카드
    message_card = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
    message_card.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 메시지 앱 선택 영역
    app_select_frame = ttk.Frame(message_card)
    app_select_frame.pack(fill="x", pady=(0, 15))
    
    ttk.Label(app_select_frame, text="메시지 앱:", style="InfoLabel.TLabel").pack(side="left", padx=(0, 5))
    
    app_var = tk.StringVar(value="기본 메시지")
    app_combo = ttk.Combobox(app_select_frame, textvariable=app_var, values=["기본 메시지", "WhatsApp", "카카오톡", "기타"])
    app_combo.pack(side="left", padx=(0, 10))
    
    ttk.Button(app_select_frame, text="조회", style="AccentButton.TButton", width=8).pack(side="left")
    
    # 메시지 표시 영역
    message_paned = ttk.PanedWindow(message_card, orient="horizontal")
    message_paned.pack(fill="both", expand=True, pady=(10, 0))
    
    # 왼쪽: 대화 목록
    convo_frame = ttk.Frame(message_paned)
    message_paned.add(convo_frame, weight=1)
    
    ttk.Label(convo_frame, text="대화 목록", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
    
    # 대화 목록 표시
    convo_list = ttk.Treeview(convo_frame, columns=("contact", "last_msg", "date"), show="headings", selectmode="browse")
    convo_list.heading("contact", text="연락처")
    convo_list.heading("last_msg", text="마지막 메시지")
    convo_list.heading("date", text="날짜")
    
    convo_list.column("contact", width=100)
    convo_list.column("last_msg", width=150)
    convo_list.column("date", width=100, anchor="center")
    
    convo_scrollbar = ttk.Scrollbar(convo_frame, orient="vertical", command=convo_list.yview)
    convo_list.configure(yscrollcommand=convo_scrollbar.set)
    
    convo_list.pack(side="left", fill="both", expand=True)
    convo_scrollbar.pack(side="right", fill="y")
    
    # 오른쪽: 메시지 내용
    message_detail_frame = ttk.Frame(message_paned)
    message_paned.add(message_detail_frame, weight=2)
    
    ttk.Label(message_detail_frame, text="메시지 내용", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
    
    # 메시지 내용 표시 영역
    message_content = tk.Text(message_detail_frame, wrap="word", state="disabled")
    message_content.pack(fill="both", expand=True)
    
    # 샘플 대화 목록 추가
    sample_convos = [
        {"contact": "홍길동", "last_msg": "안녕하세요", "date": "2025-03-17"},
        {"contact": "이철수", "last_msg": "내일 만나요", "date": "2025-03-16"},
        {"contact": "김영희", "last_msg": "확인했습니다", "date": "2025-03-15"},
    ]
    
    for convo in sample_convos:
        convo_list.insert("", "end", values=(convo["contact"], convo["last_msg"], convo["date"]))