import tkinter as tk
from tkinter import ttk

def create_file_list_frame(parent, colors):
    """파일 리스트 프레임을 생성합니다."""
    frame = ttk.Frame(parent, padding=5)
    
    # 프레임 헤더
    header_frame = ttk.Frame(frame)
    header_frame.pack(fill="x", pady=(0, 5))
    
    # 아이콘과 제목
    icon_label = ttk.Label(header_frame, text="📋", font=("Arial", 12))
    icon_label.pack(side="left", padx=(0, 5))
    ttk.Label(header_frame, text="파일 목록", style="Subheader.TLabel").pack(side="left")
    
    # 검색 프레임
    search_frame = ttk.Frame(frame, style="Search.TFrame")
    search_frame.pack(fill="x", pady=(0, 10))
    
    # 검색 레이블과 입력 필드
    search_icon = ttk.Label(search_frame, text="🔍", font=("Arial", 10))
    search_icon.pack(side="left", padx=(5, 0))
    
    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var)
    search_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
    
    # 필터 콤보박스
    ttk.Label(search_frame, text="필터:").pack(side="left", padx=(10, 5))
    filter_var = tk.StringVar()
    filter_combo = ttk.Combobox(search_frame, textvariable=filter_var, width=12)
    filter_combo['values'] = ('모든 파일', '이미지', '문서', '데이터베이스', '설정 파일')
    filter_combo.current(0)
    filter_combo.pack(side="left", padx=5, pady=5)
    
    # 검색 버튼
    search_btn = ttk.Button(search_frame, text="검색", width=8)
    search_btn.pack(side="right", padx=5, pady=5)
    
    # 파일 목록 테이블
    table_frame = ttk.Frame(frame)
    table_frame.pack(fill="both", expand=True)
    
    # 파일 목록을 위한 트리뷰 (향상된 디자인)
    columns = ('name', 'size', 'type', 'date', 'permission')
    file_list_tree = ttk.Treeview(table_frame, columns=columns, show='headings', style="FileList.Treeview")
    
    # 컬럼 헤더 설정
    file_list_tree.heading('name', text='파일명')
    file_list_tree.heading('size', text='크기')
    file_list_tree.heading('type', text='유형')
    file_list_tree.heading('date', text='수정일')
    file_list_tree.heading('permission', text='권한')
    
    # 컬럼 폭 설정
    file_list_tree.column('name', width=250)
    file_list_tree.column('size', width=80, anchor='e')
    file_list_tree.column('type', width=100)
    file_list_tree.column('date', width=140)
    file_list_tree.column('permission', width=80)
    
    file_list_tree.pack(side="left", fill="both", expand=True)
    
    # 수직 스크롤바
    v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=file_list_tree.yview)
    v_scrollbar.pack(side="right", fill="y")
    file_list_tree.configure(yscrollcommand=v_scrollbar.set)
    
    # 수평 스크롤바
    h_scrollbar = ttk.Scrollbar(frame, orient="horizontal", command=file_list_tree.xview)
    h_scrollbar.pack(fill="x")
    file_list_tree.configure(xscrollcommand=h_scrollbar.set)
    
    # 파일 정보 요약 (향상된 정보 영역)
    info_frame = ttk.Frame(frame, style="InfoBar.TFrame", padding=5)
    info_frame.pack(fill="x", pady=5)
    
    # 파일 정보 뱃지
    file_count_label = ttk.Label(info_frame, text="항목: 0", style="Badge.TLabel", padding=(8, 3))
    file_count_label.pack(side="left", padx=(0, 10))
    
    selected_label = ttk.Label(info_frame, text="선택: 0", style="Badge.TLabel", padding=(8, 3))
    selected_label.pack(side="left", padx=10)
    
    total_size_label = ttk.Label(info_frame, text="총 크기: 0 KB", style="Badge.TLabel", padding=(8, 3))
    total_size_label.pack(side="left", padx=10)
    
    # 파일 작업 버튼 (향상된 버튼 디자인)
    button_frame = ttk.Frame(frame)
    button_frame.pack(fill="x", pady=(5, 0))
    
    # 각 버튼에 아이콘 추가
    open_btn = ttk.Button(button_frame, text="✏️ 파일 열기", width=14, style="Action.TButton")
    open_btn.pack(side="left", padx=(0, 5))
    
    extract_btn = ttk.Button(button_frame, text="📤 추출", width=10, style="Action.TButton")
    extract_btn.pack(side="left", padx=5)
    
    export_btn = ttk.Button(button_frame, text="📋 내보내기", width=12, style="Action.TButton")
    export_btn.pack(side="left", padx=5)
    
    # 오른쪽 정렬된 버튼
    refresh_btn = ttk.Button(button_frame, text="🔄 새로고침", width=12, style="Action.TButton")
    refresh_btn.pack(side="right", padx=(5, 0))
    
    # 컨텍스트 메뉴
    context_menu = tk.Menu(file_list_tree, tearoff=0)
    context_menu.add_command(label="열기")
    context_menu.add_command(label="추출")
    context_menu.add_command(label="내보내기")
    context_menu.add_separator()
    context_menu.add_command(label="메타데이터 보기")
    context_menu.add_separator()
    context_menu.add_command(label="속성")
    
    def show_context_menu(event):
        context_menu.post(event.x_root, event.y_root)
    
    file_list_tree.bind("<Button-3>", show_context_menu)
    
    return {
        'file_list_frame': frame,
        'file_list_tree': file_list_tree,
        'file_list_scrollbar': v_scrollbar,
        'file_count_label': file_count_label,
        'selected_label': selected_label,
        'total_size_label': total_size_label
    }