from tkinter import ttk, messagebox
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from artifact_analyzer.call.call_history import CallHistoryAnalyzer


def display_call_history(parent_frame, backup_path):
    """통화 기록을 표시하는 함수입니다."""
    # 기존 위젯 삭제
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # CallHistoryAnalyzer 인스턴스 생성
    analyzer = CallHistoryAnalyzer(backup_path)
    success, message = analyzer.load_call_records()
    
    # 메인 프레임 생성
    main_frame = ttk.Frame(parent_frame)
    main_frame.pack(fill="both", expand=True)
    
    # 상단 검색 및 필터 영역
    search_frame = ttk.Frame(main_frame, style="Card.TFrame", padding=10)
    search_frame.pack(fill="x", padx=5, pady=5)
    
    # 검색창
    ttk.Label(search_frame, text="검색:").pack(side="left", padx=(0, 5))
    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
    search_entry.pack(side="left", padx=5)
    
    # 필터 옵션 (수신/발신/부재중)
    filter_var = tk.StringVar(value="모든 통화")
    filter_options = ["모든 통화", "수신 통화", "발신 통화", "부재중 통화"]
    filter_combobox = ttk.Combobox(search_frame, textvariable=filter_var, values=filter_options, state="readonly", width=15)
    filter_combobox.pack(side="left", padx=10)
    
    # 날짜 범위 선택
    ttk.Label(search_frame, text="기간:").pack(side="left", padx=(10, 5))
    date_range_var = tk.StringVar(value="전체")
    date_options = ["전체", "오늘", "어제", "이번 주", "이번 달"]
    date_combobox = ttk.Combobox(search_frame, textvariable=date_range_var, values=date_options, state="readonly", width=15)
    date_combobox.pack(side="left", padx=5)
    
    # 검색 버튼
    search_button = ttk.Button(search_frame, text="검색", style="Accent.TButton")
    search_button.pack(side="left", padx=10)
    
    # 좌우 패널을 위한 PanedWindow
    paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
    paned_window.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 왼쪽 패널 - 통화 목록
    left_frame = ttk.Frame(paned_window, style="Card.TFrame", padding=10)
    paned_window.add(left_frame, weight=1)
    
    # 통화 목록 헤더
    ttk.Label(left_frame, text="통화 기록", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))
    
    # 통화 목록 트리뷰
    columns = ("id", "number", "date", "duration", "direction", "answered")
    call_treeview = ttk.Treeview(left_frame, columns=columns, show="headings", height=20)
    
    # 컬럼 설정
    call_treeview.heading("id", text="ID")
    call_treeview.heading("number", text="전화번호")
    call_treeview.heading("date", text="날짜/시간")
    call_treeview.heading("duration", text="통화시간(초)")
    call_treeview.heading("direction", text="방향")
    call_treeview.heading("answered", text="응답여부")
    
    # 컬럼 너비 설정
    call_treeview.column("id", width=50)
    call_treeview.column("number", width=130)
    call_treeview.column("date", width=200)
    call_treeview.column("duration", width=80)
    call_treeview.column("direction", width=60)
    call_treeview.column("answered", width=70)
    
    # 스크롤바 추가
    scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=call_treeview.yview)
    call_treeview.configure(yscrollcommand=scrollbar.set)
    
    # 트리뷰와 스크롤바 배치
    call_treeview.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # 오른쪽 패널 - 상세 정보 및 통계
    right_frame = ttk.Frame(paned_window, style="Card.TFrame", padding=10)
    paned_window.add(right_frame, weight=1)
    
    # 탭 컨트롤 생성
    tab_control = ttk.Notebook(right_frame)
    tab_control.pack(fill="both", expand=True)
    
    # 상세 정보 탭
    details_tab = ttk.Frame(tab_control)
    tab_control.add(details_tab, text="상세 정보")
    
    # 상세 정보 프레임
    details_frame = ttk.Frame(details_tab, style="SubCard.TFrame", padding=10)
    details_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 상세 정보 레이블 (백엔드의 CallRecord 속성에 맞게 수정)
    detail_labels = {
        "number_label": ttk.Label(details_frame, text="전화번호:"),
        "date_label": ttk.Label(details_frame, text="날짜/시간:"),
        "duration_label": ttk.Label(details_frame, text="통화시간(초):"),
        "direction_label": ttk.Label(details_frame, text="통화방향:"),
        "answered_label": ttk.Label(details_frame, text="응답여부:"),
        "id_label": ttk.Label(details_frame, text="레코드 ID:")
    }
    
    detail_values = {
        "number_value": ttk.Label(details_frame, text="", style="DetailValue.TLabel"),
        "date_value": ttk.Label(details_frame, text="", style="DetailValue.TLabel"),
        "duration_value": ttk.Label(details_frame, text="", style="DetailValue.TLabel"),
        "direction_value": ttk.Label(details_frame, text="", style="DetailValue.TLabel"),
        "answered_value": ttk.Label(details_frame, text="", style="DetailValue.TLabel"),
        "id_value": ttk.Label(details_frame, text="", style="DetailValue.TLabel")
    }
    
    # 그리드 배치
    row = 0
    for key, label in detail_labels.items():
        label.grid(row=row, column=0, sticky="w", padx=5, pady=5)
        value_key = key.replace("label", "value")
        detail_values[value_key].grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1
    
    # 통계 탭
    stats_tab = ttk.Frame(tab_control)
    tab_control.add(stats_tab, text="통계")
    
    # 통계 프레임
    stats_frame = ttk.Frame(stats_tab, style="SubCard.TFrame", padding=10)
    stats_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 통계 정보 레이블
    ttk.Label(stats_frame, text="통화 통계", style="SubCardHeader.TLabel").pack(anchor="w", pady=(0, 10))
    
    # 통계 데이터 프레임
    stats_data_frame = ttk.Frame(stats_frame)
    stats_data_frame.pack(fill="x", expand=False, pady=5)
    
    # 통계 정보 그리드 (백엔드의 get_call_statistics() 결과에 맞게 수정)
    stats_labels = [
        ("총 통화수:", "0"),
        ("수신 통화:", "0"),
        ("발신 통화:", "0"),
        ("부재중 통화:", "0"),
        ("총 통화시간:", "0초"),
        ("평균 통화시간:", "0초"),
        ("가장 긴 통화:", "0초"),
        ("가장 많이 통화한 번호:", "없음")
    ]
    
    stats_values = {}
    for i, (label_text, value_text) in enumerate(stats_labels):
        ttk.Label(stats_data_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=5, pady=2)
        stats_values[label_text] = ttk.Label(stats_data_frame, text=value_text, style="DetailValue.TLabel")
        stats_values[label_text].grid(row=i, column=1, sticky="w", padx=5, pady=2)
    
    # 그래프를 위한 프레임
    graph_frame = ttk.Frame(stats_frame)
    graph_frame.pack(fill="both", expand=True, pady=10)
    
    # 삭제된 기록 탭
    deleted_tab = ttk.Frame(tab_control)
    tab_control.add(deleted_tab, text="삭제된 기록")
    
    # 삭제된 기록 프레임
    deleted_frame = ttk.Frame(deleted_tab, style="SubCard.TFrame", padding=10)
    deleted_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    ttk.Label(deleted_frame, text="삭제된 통화 기록 정보", style="SubCardHeader.TLabel").pack(anchor="w", pady=(0, 10))
    
    # 삭제된 기록 정보 프레임 (백엔드의 get_deleted_record_info() 결과에 맞게 수정)
    deleted_info_frame = ttk.Frame(deleted_frame)
    deleted_info_frame.pack(fill="x", expand=False, pady=5)
    
    deleted_info_labels = [
        ("최대 레코드 ID:", "0"),
        ("현재 레코드 수:", "0"),
        ("삭제된 레코드 수 (추정):", "0")
    ]
    
    deleted_info_values = {}
    for i, (label_text, value_text) in enumerate(deleted_info_labels):
        ttk.Label(deleted_info_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=5, pady=2)
        deleted_info_values[label_text] = ttk.Label(deleted_info_frame, text=value_text, style="DetailValue.TLabel")
        deleted_info_values[label_text].grid(row=i, column=1, sticky="w", padx=5, pady=2)
    
    # 데이터베이스에서 통화 기록 로드 및 표시
    def load_call_history():
        """백업에서 통화 기록을 로드하고 표시합니다."""
        # 트리뷰 비우기
        for item in call_treeview.get_children():
            call_treeview.delete(item)
        
        if not success:
            messagebox.showerror("오류", message)
            return
            
        # 통화 기록 표시
        for idx, record in enumerate(analyzer.call_records):
            call_treeview.insert("", "end", values=(
                record.z_pk,
                record.address,
                record.call_date,
                record.duration,
                record.direction,
                record.is_answered
            ))
            
        # 통계 업데이트
        stats = analyzer.get_call_statistics()
        stats_values["총 통화수:"].config(text=str(stats["total_calls"]))
        stats_values["수신 통화:"].config(text=str(stats["incoming_calls"]))
        stats_values["발신 통화:"].config(text=str(stats["outgoing_calls"]))
        stats_values["부재중 통화:"].config(text=str(stats["missed_calls"]))
        stats_values["총 통화시간:"].config(text=f"{stats['total_duration']}초")
        stats_values["평균 통화시간:"].config(text=f"{stats['avg_duration']:.1f}초")
        stats_values["가장 긴 통화:"].config(text=f"{stats['max_duration']}초")
        stats_values["가장 많이 통화한 번호:"].config(text=stats["top_called_number"] or "없음")
        
        # 삭제된 기록 정보 업데이트
        deleted_info = analyzer.get_deleted_record_info()
        deleted_info_values["최대 레코드 ID:"].config(text=str(deleted_info["max_pk"]))
        deleted_info_values["현재 레코드 수:"].config(text=str(deleted_info["record_count"]))
        deleted_info_values["삭제된 레코드 수 (추정):"].config(text=str(deleted_info["missing_count"]))
        
        # 그래프 생성
        create_graphs(analyzer)
    
    # 그래프 생성 함수
    def create_graphs(analyzer):
        """통화 통계 그래프를 생성합니다."""
        # 기존 그래프 위젯 제거
        for widget in graph_frame.winfo_children():
            widget.destroy()
            
        # 그래프 프레임 
        fig = plt.Figure(figsize=(6, 4), dpi=100)
        
        # 그래프 1: 날짜별 통화 횟수
        date_counts = analyzer.get_calls_by_date()
        if date_counts:
            ax1 = fig.add_subplot(211)  # 2행 1열 중 1번째
            dates = list(date_counts.keys())[-10:]  # 최근 10일만
            counts = [date_counts[date] for date in dates]
            ax1.bar(range(len(dates)), counts, color='royalblue')
            ax1.set_xticks(range(len(dates)))
            ax1.set_xticklabels([d.split()[0].replace('년 ', '\n').replace('월 ', '/') for d in dates], rotation=45, fontsize=8)
            ax1.set_title('날짜별 통화 횟수')
            
        # 그래프 2: 통화 유형별 비율
        type_counts = analyzer.get_calls_by_type()
        if type_counts:
            ax2 = fig.add_subplot(212)  # 2행 1열 중 2번째
            labels = list(type_counts.keys())
            sizes = list(type_counts.values())
            colors = ['lightcoral', 'lightskyblue', 'lightgreen']
            ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax2.axis('equal')
            ax2.set_title('통화 유형별 비율')
            
        # 캔버스에 그래프 추가
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # 통화 선택 시 상세 정보 표시
    def show_call_details(event):
        """선택한 통화의 상세 정보를 표시합니다."""
        selected_item = call_treeview.selection()
        if not selected_item:
            return
        
        # 선택된 항목의 값 가져오기
        values = call_treeview.item(selected_item, "values")
        
        # 상세 정보 업데이트
        if len(values) >= 6:
            detail_values["id_value"].config(text=values[0])
            detail_values["number_value"].config(text=values[1])
            detail_values["date_value"].config(text=values[2])
            detail_values["duration_value"].config(text=values[3])
            detail_values["direction_value"].config(text=values[4])
            detail_values["answered_value"].config(text=values[5])
    
    # 검색 함수
    def search_calls():
        """통화 기록을 검색합니다."""
        # 트리뷰 비우기
        for item in call_treeview.get_children():
            call_treeview.delete(item)
            
        # 검색 조건 가져오기
        search_query = search_var.get()
        call_type = filter_var.get() if filter_var.get() != "모든 통화" else None
        date_range = date_range_var.get() if date_range_var.get() != "전체" else None
        
        # 검색 수행
        filtered_records = analyzer.search_call_records(search_query, call_type, date_range)
        
        # 결과 표시
        for record in filtered_records:
            call_treeview.insert("", "end", values=(
                record.z_pk,
                record.address,
                record.call_date,
                record.duration,
                record.direction,
                record.is_answered
            ))
    
    # 이벤트 바인딩
    call_treeview.bind("<<TreeviewSelect>>", show_call_details)
    search_button.config(command=search_calls)
    
    # 초기 데이터 로드
    load_call_history()
    
    return main_frame