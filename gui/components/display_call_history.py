from tkinter import ttk, messagebox
import tkinter as tk
from artifact_analyzer.call.call_history import CallHistoryAnalyzer


def display_call_history(parent_frame, backup_path):
    """통화 기록을 표시하는 함수입니다."""
    # 기존 위젯 삭제
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # 백업 경로 디버깅
    print(f"백업 경로: {backup_path}")
    
    # CallHistoryAnalyzer 인스턴스 생성
    analyzer = CallHistoryAnalyzer(backup_path)
    success, message = analyzer.load_call_records()
    
    # 로드 결과 디버깅
    print(f"통화 기록 로드 결과: {success}, 메시지: {message}")
    if success:
        print(f"로드된 통화 기록 수: {len(analyzer.call_records) if hasattr(analyzer, 'call_records') else 0}")
    
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
    
    # 오른쪽 패널 - 상세 정보
    right_frame = ttk.Frame(paned_window, style="Card.TFrame", padding=10)
    paned_window.add(right_frame, weight=1)
    
    # 상세 정보 프레임
    details_frame = ttk.Frame(right_frame, style="SubCard.TFrame", padding=10)
    details_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 상세 정보 헤더
    header_label = ttk.Label(details_frame, text="상세 정보", style="SubCardHeader.TLabel")
    header_label.pack(anchor="w", pady=(0, 10))
    
    # 상세 정보를 위한 내부 프레임 생성 (grid 레이아웃용)
    details_grid_frame = ttk.Frame(details_frame)
    details_grid_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 상세 정보 레이블 (백엔드의 CallRecord 속성에 맞게 수정)
    detail_labels = {
        "number_label": ttk.Label(details_grid_frame, text="전화번호:"),
        "date_label": ttk.Label(details_grid_frame, text="날짜/시간:"),
        "duration_label": ttk.Label(details_grid_frame, text="통화시간(초):"),
        "direction_label": ttk.Label(details_grid_frame, text="통화방향:"),
        "answered_label": ttk.Label(details_grid_frame, text="응답여부:"),
        "id_label": ttk.Label(details_grid_frame, text="레코드 ID:")
    }
    
    detail_values = {
        "number_value": ttk.Label(details_grid_frame, text="", style="DetailValue.TLabel"),
        "date_value": ttk.Label(details_grid_frame, text="", style="DetailValue.TLabel"),
        "duration_value": ttk.Label(details_grid_frame, text="", style="DetailValue.TLabel"),
        "direction_value": ttk.Label(details_grid_frame, text="", style="DetailValue.TLabel"),
        "answered_value": ttk.Label(details_grid_frame, text="", style="DetailValue.TLabel"),
        "id_value": ttk.Label(details_grid_frame, text="", style="DetailValue.TLabel")
    }
    
    # 그리드 배치
    row = 0
    for key, label in detail_labels.items():
        label.grid(row=row, column=0, sticky="w", padx=5, pady=5)
        value_key = key.replace("label", "value")
        detail_values[value_key].grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1
    
    # 데이터베이스에서 통화 기록 로드 및 표시
    def load_call_history():
        """백업에서 통화 기록을 로드하고 표시합니다."""
        # 트리뷰 비우기
        for item in call_treeview.get_children():
            call_treeview.delete(item)
        
        if not success:
            messagebox.showerror("오류", message)
            # 오류 메시지를 화면에도 표시
            error_label = ttk.Label(left_frame, text=f"오류: {message}", foreground="red")
            error_label.pack(pady=10)
            return
            
        # 통화 기록이 비어있는 경우
        if not hasattr(analyzer, 'call_records') or len(analyzer.call_records) == 0:
            empty_label = ttk.Label(left_frame, text="통화 기록이 없습니다.")
            empty_label.pack(pady=20)
            print("통화 기록이 비어 있습니다.")
            return
            
        # 통화 기록 표시
        print(f"트리뷰에 {len(analyzer.call_records)}개 기록 추가 시작")
        for idx, record in enumerate(analyzer.call_records):
            try:
                # 기록 확인을 위한 디버깅 출력
                if idx < 5:  # 처음 5개만 출력
                    print(f"기록 {idx}: {record.z_pk}, {record.address}, {record.call_date}")
                
                call_treeview.insert("", "end", values=(
                    record.z_pk,
                    record.address,
                    record.call_date,
                    record.duration,
                    record.direction,
                    record.is_answered
                ))
            except Exception as e:
                print(f"기록 {idx} 추가 중 오류: {e}")
    
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
    try:
        load_call_history()
        print("초기 데이터 로드 완료")
    except Exception as e:
        print(f"초기 데이터 로드 중 오류 발생: {e}")
        messagebox.showerror("오류", f"데이터 로드 중 오류가 발생했습니다: {e}")
    
    # 메인 프레임이 제대로 표시되는지 확인
    main_frame.update()
    print(f"메인 프레임 크기: {main_frame.winfo_width()}x{main_frame.winfo_height()}")
    print(f"메인 프레임 위젯 수: {len(main_frame.winfo_children())}")
    
    return main_frame