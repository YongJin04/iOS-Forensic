import tkinter as tk
from tkinter import ttk

def display_call_history(content_frame, backup_path):
    """통화 기록을 콘텐츠 프레임에 표시합니다."""
    # 기존 위젯 삭제
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    # 헤더 추가
    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill="x", pady=(0, 10))
    
    ttk.Label(header_frame, text="📞 통화 기록", style="ContentHeader.TLabel").pack(side="left")
    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))
    
    # 통화 기록 카드
    call_card = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
    call_card.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 필터 영역
    filter_frame = ttk.Frame(call_card)
    filter_frame.pack(fill="x", pady=(0, 15))
    
    ttk.Label(filter_frame, text="통화 유형:", style="InfoLabel.TLabel").pack(side="left", padx=(0, 5))
    
    call_type_var = tk.StringVar(value="모든 통화")
    call_type_combo = ttk.Combobox(filter_frame, textvariable=call_type_var, 
                                  values=["모든 통화", "수신", "발신", "부재중"])
    call_type_combo.pack(side="left", padx=(0, 15))
    
    ttk.Label(filter_frame, text="기간:", style="InfoLabel.TLabel").pack(side="left", padx=(0, 5))
    
    period_var = tk.StringVar(value="전체")
    period_combo = ttk.Combobox(filter_frame, textvariable=period_var, 
                               values=["전체", "오늘", "이번 주", "이번 달", "지난 달"])
    period_combo.pack(side="left", padx=(0, 10))
    
    ttk.Button(filter_frame, text="조회", style="AccentButton.TButton", width=8).pack(side="left")
    
    # 통화 기록 표시 영역
    call_frame = ttk.Frame(call_card)
    call_frame.pack(fill="both", expand=True, pady=(10, 0))
    
    # 통화 기록 테이블
    columns = ("name", "number", "type", "date", "duration")
    call_tree = ttk.Treeview(call_frame, columns=columns, show="headings", selectmode="browse")
    
    # 헤더 설정
    call_tree.heading("name", text="이름")
    call_tree.heading("number", text="전화번호")
    call_tree.heading("type", text="유형")
    call_tree.heading("date", text="날짜/시간")
    call_tree.heading("duration", text="통화 시간")
    
    # 컬럼 너비 설정
    call_tree.column("name", width=100)
    call_tree.column("number", width=120)
    call_tree.column("type", width=80, anchor="center")
    call_tree.column("date", width=150, anchor="center")
    call_tree.column("duration", width=100, anchor="center")
    
    # 스크롤바 추가
    scrollbar = ttk.Scrollbar(call_frame, orient="vertical", command=call_tree.yview)
    call_tree.configure(yscrollcommand=scrollbar.set)
    
    # 패킹
    call_tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # 샘플 데이터 추가 (실제로는 백업에서 추출)
    sample_calls = [
        {"name": "홍길동", "number": "010-1234-5678", "type": "수신", "date": "2025-03-17 14:30", "duration": "02:45"},
        {"name": "이철수", "number": "010-8765-4321", "type": "발신", "date": "2025-03-16 09:15", "duration": "01:20"},
        {"name": "김영희", "number": "010-9876-5432", "type": "부재중", "date": "2025-03-15 18:45", "duration": "--:--"},
        {"name": "박지성", "number": "010-1111-2222", "type": "수신", "date": "2025-03-14 13:20", "duration": "00:45"},
        {"name": "최민수", "number": "010-3333-4444", "type": "발신", "date": "2025-03-13 16:50", "duration": "05:12"},
    ]
    
    for call in sample_calls:
        call_tree.insert("", "end", values=(call["name"], call["number"], call["type"], 
                                          call["date"], call["duration"]))