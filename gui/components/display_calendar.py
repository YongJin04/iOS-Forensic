import tkinter as tk
from tkinter import ttk, messagebox
import calendar
from datetime import datetime, timedelta
import pandas as pd
from functools import partial

# 백엔드 모듈 임포트 (포렌식 기능이 통합된 CalendarAnalyser)
from artifact_analyzer.calendar.calendar_analyzer import CalendarAnalyser

def display_calendar(parent_frame, backup_path):
    """
    창 크기에 맞춰 균등 확장되는 달력 UI를 표시합니다.
    
    특징:
    - 반응형 그리드 레이아웃으로 창 크기에 맞게 자동 조절됨
    - 다중일정(여러 날짜)에 걸친 이벤트 자동 감지 및 표시
    - 이벤트 더블클릭 시 스크롤 가능한 통합 상세 정보 팝업
    - 메모리 최적화를 위한 지연 로딩 및 캐싱 구현
    
    Args:
        parent_frame: 달력을 표시할 부모 위젯
        backup_path: 캘린더 백업 파일 경로
    """
    # 기존 위젯 삭제 (메모리 최적화)
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # 전역 변수 캐싱을 위한 클래스 (상태 관리)
    class CalendarState:
        def __init__(self):
            self.current_date = datetime.now()
            self.current_year = self.current_date.year
            self.current_month = self.current_date.month
            self.events_cache = {}  # {year-month: events_df} 형식으로 이벤트 캐싱
            
    state = CalendarState()
    
    # ===== 유틸리티 함수 =====
    
    def normalize_color(color_str):
        """
        색상 문자열을 정규화합니다. (예: "#RRGGBBAA" → "#RRGGBB")
        
        Args:
            color_str: 정규화할 색상 문자열
            
        Returns:
            정규화된 색상 문자열
        """
        if isinstance(color_str, str) and len(color_str) == 9:
            return color_str[:7]  # 알파 채널 제거
        return color_str or "#FFFFFF"  # 기본값: 흰색
    
    def create_tooltip(widget, text):
        """
        위젯에 마우스 오버 툴팁을 추가합니다.
        
        Args:
            widget: 툴팁을 추가할 위젯
            text: 툴팁에 표시할 텍스트
        """
        tooltip = None
        
        def enter(event):
            nonlocal tooltip
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # 툴팁 생성
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            label = ttk.Label(tooltip, text=text, background="lightyellow", 
                             relief="solid", borderwidth=1, padding=(5, 3))
            label.pack()
            
        def leave(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    
    # ===== UI 스타일 설정 =====
    
    def setup_styles():
        """캘린더 UI의 모든 스타일을 설정합니다."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 일반 텍스트/레이블 스타일
        style.configure("HeaderLarge.TLabel", font=("Helvetica", 18, "bold"), foreground="#2C3E50")
        style.configure("Header.TLabel", font=("Helvetica", 14, "bold"), foreground="#34495E")
        style.configure("HeaderSmall.TLabel", font=("Helvetica", 10, "bold"), foreground="#2980B9")
        style.configure("Text.TLabel", font=("Helvetica", 10), foreground="#2C3E50", background="white")
        style.configure("SmallText.TLabel", font=("Helvetica", 8), foreground="#7F8C8D")
        
        # 날짜 셀 스타일
        style.configure("DayCell.TFrame", background="#FFFFFF", relief="groove", borderwidth=1)
        style.configure("WeekendCell.TFrame", background="#F8F9FA", relief="groove", borderwidth=1)
        style.configure("TodayCell.TFrame", background="#E8F4FD", relief="groove", borderwidth=1)
        
        # 이벤트 레이블 스타일
        style.configure("Event.TLabel", font=("Helvetica", 9), background="#3498DB", foreground="white")
        
        # 버튼 및 내비게이션 스타일
        style.configure("Nav.TButton", font=("Helvetica", 10), padding=5)
        style.configure("Today.TButton", font=("Helvetica", 9), padding=3)
        
        # 기본 프레임 스타일
        style.configure("Calendar.TFrame", background="#FDFDFD")
        style.configure("EventDetail.TFrame", relief="groove", borderwidth=1, padding=8)
        
        # 오류 메시지 스타일
        style.configure("ErrorText.TLabel", font=("Helvetica", 12), foreground="red")
        
    setup_styles()
    
    # ===== 캘린더 분석기 초기화 =====
    
    try:
        # CalendarAnalyser 객체 생성 및 DB 연결
        cal_analyser = CalendarAnalyser(backup_path)
        if not cal_analyser.connect_to_db():
            messagebox.showerror("오류", "캘린더 DB를 찾을 수 없거나 연결할 수 없습니다.")
            ttk.Label(parent_frame, text="DB 연결 실패. 백업 경로를 확인하세요.", 
                     style="ErrorText.TLabel").pack(pady=20)
            return
    except Exception as e:
        messagebox.showerror("오류", f"분석기 초기화 오류: {str(e)}")
        ttk.Label(parent_frame, text=f"초기화 실패: {str(e)}", 
                 style="ErrorText.TLabel").pack(pady=20)
        return
    
    # ===== 상단 헤더 및 네비게이션 영역 =====
    
    # 헤더 (제목)
    header_frame = ttk.Frame(parent_frame)
    header_frame.pack(fill="x", pady=(0, 5))
    
    header_label = ttk.Label(header_frame, text="캘린더 분석", style="HeaderLarge.TLabel")
    header_label.pack(side="left", pady=(0, 5))
    
    # 현재 월 표시 레이블
    month_label_var = tk.StringVar()
    
    def update_month_label():
        """월 표시 레이블 텍스트를 현재 선택된 년/월로 업데이트"""
        month_label_var.set(f"{state.current_year}년 {state.current_month}월")
    
    update_month_label()
    
    # 네비게이션 프레임
    nav_frame = ttk.Frame(parent_frame)
    nav_frame.pack(fill="x", pady=5)
    
    # 이전 월 버튼
    prev_month_btn = ttk.Button(nav_frame, text="◀ 이전", 
                              command=lambda: change_month(-1), style="Nav.TButton")
    prev_month_btn.pack(side="left")
    create_tooltip(prev_month_btn, "이전 달로 이동")
    
    # 월 표시 레이블
    month_label = ttk.Label(nav_frame, textvariable=month_label_var, style="Header.TLabel")
    month_label.pack(side="left", padx=10)
    
    # 다음 월 버튼
    next_month_btn = ttk.Button(nav_frame, text="다음 ▶", 
                              command=lambda: change_month(1), style="Nav.TButton")
    next_month_btn.pack(side="left")
    create_tooltip(next_month_btn, "다음 달로 이동")
    
    # 오늘로 이동 버튼
    today_btn = ttk.Button(nav_frame, text="오늘", 
                          command=lambda: go_to_today(), style="Today.TButton")
    today_btn.pack(side="right", padx=5)
    create_tooltip(today_btn, "오늘 날짜로 이동")
    
    # ===== 메인 달력 프레임 =====
    
    calendar_frame = ttk.Frame(parent_frame, style="Calendar.TFrame")
    calendar_frame.pack(fill="both", expand=True, pady=10)
    
    # 동일한 셀 크기 보장을 위해 행과 열 weight 설정 
    # (요일 헤더 포함 7행, 7열 - 월요일부터 일요일까지)
    for r in range(7):  # 0: 요일 헤더, 1-6: 달력 행
        calendar_frame.rowconfigure(r, weight=1)
    for c in range(7):  # 0-6: 월-일
        calendar_frame.columnconfigure(c, weight=1)
    
    # ===== 이벤트 로딩 및 달력 표시 함수 =====
    
    def load_events():
        """
        현재 선택된 월의 이벤트를 로드하고 일자별로 그룹화합니다.
        
        캐싱: 이미 로드된 월은 다시 DB에서 가져오지 않고 캐시에서 반환
        
        Returns:
            dict: {일자: [이벤트 목록]} 형태의 사전
        """
        # 캐시 키 생성
        cache_key = f"{state.current_year}-{state.current_month}"
        
        # 캐시된 데이터가 있으면 재사용
        if cache_key in state.events_cache:
            events_df = state.events_cache[cache_key]
        else:
            # DB에서 이벤트 로드 및 캐싱
            events_df = cal_analyser.get_events_for_month(state.current_year, state.current_month)
            state.events_cache[cache_key] = events_df
        
        # 일자별로 이벤트 그룹화
        events_by_day = {}
        
        # 멀티데이 이벤트 처리 (시작일부터 종료일까지의 모든 날짜에 이벤트 표시)
        for _, event in events_df.iterrows():
            start_dt = event['start_date']
            end_dt = event['end_date'] if 'end_date' in event and event['end_date'] else start_dt
            
            # 유효한 날짜 검증
            if not start_dt:
                continue
                
            # 멀티데이 이벤트 전체 기간에 대해 처리
            curr_day = start_dt.date()
            end_day = end_dt.date() if end_dt else curr_day
            
            # 이벤트가 여러 날에 걸쳐 있는 경우
            while curr_day <= end_day:
                # 현재 표시 중인 월에 속하는 날짜만 처리
                if curr_day.month == state.current_month and curr_day.year == state.current_year:
                    day_num = curr_day.day
                    # 해당 날짜의 이벤트 목록에 추가
                    if day_num not in events_by_day:
                        events_by_day[day_num] = []
                    
                    # 동일 이벤트가 중복 추가되지 않도록 처리
                    event_id = event.get('event_id')
                    if not any(e.get('event_id') == event_id for e in events_by_day[day_num]):
                        events_by_day[day_num].append(event)
                        
                # 다음날로 이동
                curr_day += timedelta(days=1)
                
        return events_by_day
    
    def refresh_calendar():
        """
        달력 UI를 현재 선택된 월에 맞게 새로 그립니다.
        - 모든 기존 위젯 제거
        - 요일 헤더 추가
        - 날짜 셀 및 이벤트 표시
        """
        # 기존 달력 위젯 제거
        for widget in calendar_frame.winfo_children():
            widget.destroy()
            
        # 이벤트 로딩
        events_by_day = load_events()
        
        # 요일 헤더 (row=0)
        days_of_week = ["월", "화", "수", "목", "금", "토", "일"]
        for col, day_name in enumerate(days_of_week):
            lbl = ttk.Label(calendar_frame, text=day_name, style="HeaderSmall.TLabel", anchor="center")
            lbl.grid(row=0, column=col, sticky="nsew", padx=2, pady=2)
            
        # 현재 날짜 확인 (오늘 표시용)
        today = datetime.now().date()
        
        # 날짜 셀 (row=1 ~ 6)
        cal_obj = calendar.Calendar(firstweekday=0)  # 월요일 시작
        month_weeks = cal_obj.monthdayscalendar(state.current_year, state.current_month)
        
        for row_idx, week in enumerate(month_weeks, start=1):
            for col_idx, day_num in enumerate(week):
                # 날짜가 0인 경우는 해당 월에 속하지 않는 날짜
                if day_num == 0:
                    empty_frame = ttk.Frame(calendar_frame)
                    empty_frame.grid(row=row_idx, column=col_idx, sticky="nsew", padx=2, pady=2)
                    continue
                    
                # 날짜 셀 스타일 결정
                cell_style = "DayCell.TFrame"
                
                # 주말 스타일 (토,일)
                if col_idx >= 5:  # 5=토요일, 6=일요일
                    cell_style = "WeekendCell.TFrame"
                    
                # 오늘 날짜 스타일
                if (day_num == today.day and 
                    state.current_month == today.month and 
                    state.current_year == today.year):
                    cell_style = "TodayCell.TFrame"
                
                # 날짜 셀 프레임 생성
                cell_frame = ttk.Frame(calendar_frame, style=cell_style)
                cell_frame.grid(row=row_idx, column=col_idx, sticky="nsew", padx=2, pady=2)
                
                # 날짜 번호 표시
                lbl_day = ttk.Label(cell_frame, text=str(day_num), style="Header.TLabel", anchor="nw")
                lbl_day.pack(anchor="nw", padx=2, pady=2)
                
                # 해당 날짜의 이벤트 표시
                if day_num in events_by_day:
                    # 해당 날짜의 이벤트가 많을 경우 스크롤러블 프레임으로 전환
                    events = events_by_day[day_num]
                    max_visible_events = 3  # 셀에 표시할 최대 이벤트 수
                    
                    # 이벤트가 많을 경우 '더보기' 표시 준비
                    show_more = len(events) > max_visible_events
                    visible_events = events[:max_visible_events]
                    
                    # 이벤트 표시
                    for i, event in enumerate(visible_events):
                        summary = event.get('summary') or "제목 없음"
                        bg_color = normalize_color(event.get('color'))
                        fg_color = get_contrast_color(bg_color)  # 배경색에 맞는 텍스트 색상
                        
                        # 이벤트 레이블 생성 (배경색 적용)
                        ev_label = tk.Label(cell_frame, text=summary, 
                                        bg=bg_color, fg=fg_color,
                                        font=("Helvetica", 9), anchor="w",
                                        relief="groove", padx=3, pady=1)
                        ev_label.pack(fill="x", padx=2, pady=1)
                        
                        # 이벤트에 툴팁 추가
                        start_dt = event.get('start_date')
                        end_dt = event.get('end_date')
                        time_str = ""
                        if start_dt:
                            time_str = start_dt.strftime('%H:%M')
                            if end_dt and end_dt != start_dt:
                                time_str += f" ~ {end_dt.strftime('%H:%M')}"
                        
                        tooltip_text = f"{summary}\n{time_str}\n{event.get('calendar_title', '')}"
                        create_tooltip(ev_label, tooltip_text)
                        
                        # 이벤트 더블클릭 이벤트 처리
                        ev_label.bind("<Double-1>", lambda e, d=day_num: show_day_details(d))
                    
                    # '더보기' 표시 (이벤트가 많을 경우)
                    if show_more:
                        more_count = len(events) - max_visible_events
                        more_label = ttk.Label(cell_frame, 
                                             text=f"+ {more_count}개 더보기...", 
                                             style="SmallText.TLabel")
                        more_label.pack(anchor="e", padx=2)
                        more_label.bind("<Button-1>", lambda e, d=day_num: show_day_details(d))
                
                # 셀 클릭 이벤트 처리
                def on_day_click(e, day=day_num):
                    show_day_details(day)
                
                # 날짜 셀 클릭 이벤트 바인딩
                cell_frame.bind("<Double-1>", on_day_click)
                lbl_day.bind("<Double-1>", on_day_click)
    
    def get_contrast_color(bg_color):
        """
        배경색에 맞는 대비 텍스트 색상을 반환합니다.
        어두운 배경색에는 밝은 텍스트, 밝은 배경색에는 어두운 텍스트를 사용합니다.
        
        Args:
            bg_color: 배경 색상 (16진수 문자열)
            
        Returns:
            대비되는 텍스트 색상 (#FFFFFF 또는 #000000)
        """
        try:
            # 16진수 색상 코드에서 RGB 값 추출
            bg_color = bg_color.lstrip('#')
            if len(bg_color) != 6:
                return "#000000"  # 기본 검정색
                
            r, g, b = int(bg_color[0:2], 16), int(bg_color[2:4], 16), int(bg_color[4:6], 16)
            
            # 색상 밝기 계산 (YIQ 공식 사용)
            # 0.299*R + 0.587*G + 0.114*B
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            
            # 기준값 128보다 밝으면 검정색, 어두우면 흰색 반환
            return "#000000" if brightness > 128 else "#FFFFFF"
        except:
            return "#000000"  # 오류 시 기본값
    
    def show_day_details(day):
        """
        선택한 날짜의 이벤트 상세 정보를 스크롤 가능한 통합 팝업으로 표시합니다.
        
        Args:
            day: 표시할 날짜
        """
        # 상세 정보 창 생성
        detail_window = tk.Toplevel(parent_frame)
        detail_window.title(f"{state.current_year}년 {state.current_month}월 {day}일 이벤트")
        detail_window.geometry("750x550")
        detail_window.transient(parent_frame)  # 부모 창 종속
        detail_window.grab_set()  # 모달 창으로 설정
        
        # 상단 헤더
        header_frame = ttk.Frame(detail_window, padding=5)
        header_frame.pack(fill="x", pady=(5, 0))
        
        header_date = datetime(state.current_year, state.current_month, day).strftime("%Y년 %m월 %d일 (%a)")
        header_label = ttk.Label(header_frame, text=header_date, style="HeaderLarge.TLabel")
        header_label.pack(side="left")
        
        # 창 닫기 버튼
        close_btn = ttk.Button(header_frame, text="닫기", command=detail_window.destroy)
        close_btn.pack(side="right")
        
        # 구분선
        separator = ttk.Separator(detail_window, orient="horizontal")
        separator.pack(fill="x", pady=5)

        # 스크롤 가능한 영역 구성: Canvas + Scrollbar + 내부 Frame
        canvas = tk.Canvas(detail_window, highlightthickness=0)
        scrollbar = ttk.Scrollbar(detail_window, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 프레임 배치
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # 내부 콘텐츠 프레임
        content_frame = ttk.Frame(canvas, padding=10)
        canvas_window = canvas.create_window((0,0), window=content_frame, anchor="nw")
        content_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # 스크롤 휠 이벤트 바인딩
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 창 종료 시 휠 이벤트 바인딩 해제
        def on_close():
            canvas.unbind_all("<MouseWheel>")
            detail_window.destroy()
        detail_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # 이벤트 로드
        events_by_day = load_events()
        events = events_by_day.get(day, [])
        
        if not events:
            ttk.Label(content_frame, text="이 날짜에 등록된 이벤트가 없습니다.", 
                     style="Text.TLabel", font=("Helvetica", 12)).pack(pady=20)
            return
            
        # 이벤트 정렬 (시작 시간 기준)
        sorted_events = sorted(events, 
                            key=lambda e: e.get('start_date', datetime.max))
        
        # 이벤트 카드 표시
        for i, event in enumerate(sorted_events):
            # 이벤트 컨테이너 프레임
            evt_frame = ttk.Frame(content_frame, style="EventDetail.TFrame")
            evt_frame.pack(fill="x", pady=4)
            
            # === 이벤트 기본 정보 추출 ===
            event_id = event.get("event_id", "")
            summary = event.get('summary') or "제목 없음"
            calendar_title = event.get('calendar_title', '')
            description = event.get('description', '')
            location = event.get('location', '')
            color = event.get('color', '')
            symbolic_color = event.get('symbolic_color_name', '')
            is_all_day = event.get('all_day', False)
            
            # 날짜/시간 정보 포맷팅
            start_dt = event.get('start_date')
            end_dt = event.get('end_date')
            start_str = start_dt.strftime('%Y-%m-%d %H:%M') if start_dt else "날짜 없음"
            
            if is_all_day:
                time_str = "전체 일정"
                if end_dt and end_dt.date() != start_dt.date():
                    time_str += f" ({start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')})"
            else:
                time_str = start_str
                if end_dt:
                    # 같은 날이면 시간만, 다른 날이면 날짜+시간 표시
                    if start_dt.date() == end_dt.date():
                        time_str += f" ~ {end_dt.strftime('%H:%M')}"
                    else:
                        time_str += f" ~ {end_dt.strftime('%Y-%m-%d %H:%M')}"
            
            # === 이벤트 헤더 (제목 + 시간) ===
            header_frame = ttk.Frame(evt_frame)
            header_frame.pack(fill="x", expand=True)
            
            # 색상 표시
            color_box = None
            if color:
                color_box = tk.Frame(header_frame, width=16, height=16, bg=normalize_color(color))
                color_box.pack(side="left", padx=(0, 5))
            
            # 제목 표시
            title_label = ttk.Label(header_frame, text=summary, style="Header.TLabel")
            title_label.pack(side="left")
            
            # 시간 표시
            time_label = ttk.Label(header_frame, text=f"({time_str})", style="SmallText.TLabel")
            time_label.pack(side="right")
            
            # === 이벤트 정보 섹션 ===
            info_frame = ttk.Frame(evt_frame)
            info_frame.pack(fill="x", pady=5)
            
            # 2열 그리드 레이아웃 (레이블 + 값)
            info_frame.columnconfigure(0, weight=0)  # 레이블 열
            info_frame.columnconfigure(1, weight=1)  # 값 열
            
            # 기본 정보 표시 함수
            def add_info_row(row, label_text, value_text, tooltip=None):
                """정보 행 추가"""
                if not value_text:
                    return row
                
                label = ttk.Label(info_frame, text=label_text+":", style="HeaderSmall.TLabel")
                label.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=2)
                
                value = ttk.Label(info_frame, text=str(value_text), style="Text.TLabel", wraplength=650)
                value.grid(row=row, column=1, sticky="w", pady=2)
                
                if tooltip:
                    create_tooltip(value, tooltip)
                    
                return row + 1
            
            # 기본 정보 행 추가   
            row = 0
            if calendar_title:
                row = add_info_row(row, "캘린더", calendar_title)
            if color and symbolic_color:
                row = add_info_row(row, "색상", f"{symbolic_color} ({color})")
            if location:
                row = add_info_row(row, "위치", location)
            if description:
                row = add_info_row(row, "설명", description)
            
            # === 포렌식 분석 정보 섹션 ===
            if event_id:
                # 포렌식 탭 컨테이너
                forensic_frame = ttk.Frame(evt_frame)
                forensic_frame.pack(fill="x", pady=5)
                
# 포렌식 정보 헤더
                forensic_header = ttk.Label(forensic_frame, text="상세 분석 정보", style="HeaderSmall.TLabel")
                forensic_header.pack(anchor="w", pady=(5, 3))
                
                # 구분선
                ttk.Separator(forensic_frame, orient="horizontal").pack(fill="x", pady=2)
                
                # 포렌식 정보 콘텐츠 프레임
                forensic_content = ttk.Frame(forensic_frame)
                forensic_content.pack(fill="x", pady=3)
                
                # === 포렌식 정보 로드 및 표시 ===
                
                # 1. 오류 로그
                errors = cal_analyser.get_error_logs(event_id)
                if errors:
                    error_frame = ttk.LabelFrame(forensic_content, text="오류 로그")
                    error_frame.pack(fill="x", pady=3)
                    
                    for i, err in enumerate(errors):
                        err_type = err.get('error_type', '')
                        err_code = err.get('error_code', '')
                        user_info = err.get('user_info', '')
                        timestamp = err.get('timestamp', '')
                        
                        err_text = f"{err_type}: {err_code}"
                        if user_info:
                            err_text += f" ({user_info})"
                        if timestamp:
                            err_text += f" - {timestamp}"
                            
                        ttk.Label(error_frame, text=err_text, style="SmallText.TLabel").pack(anchor="w", padx=5)
                
                # 2. 외부 연동 정보
                actions = cal_analyser.get_event_actions(event_id)
                if actions:
                    action_frame = ttk.LabelFrame(forensic_content, text="외부 연동")
                    action_frame.pack(fill="x", pady=3)
                    
                    for act in actions:
                        ext_id = act.get('external_id', '')
                        ext_tag = act.get('external_mod_tag', '')
                        
                        act_text = f"ID: {ext_id}"
                        if ext_tag:
                            act_text += f", Tag: {ext_tag}"
                            
                        ttk.Label(action_frame, text=act_text, style="SmallText.TLabel").pack(anchor="w", padx=5)
                
                # 3. 반복 일정 정보
                recurrences = cal_analyser.get_recurrence_info(event_id)
                if recurrences:
                    rec_frame = ttk.LabelFrame(forensic_content, text="반복 규칙")
                    rec_frame.pack(fill="x", pady=3)
                    
                    for rec in recurrences:
                        freq = rec.get('frequency', '')
                        interval = rec.get('interval', '')
                        until = rec.get('until_date', '')
                        count = rec.get('count', '')
                        
                        # 반복 주기 한글화
                        freq_korean = {
                            'DAILY': '매일', 
                            'WEEKLY': '매주', 
                            'MONTHLY': '매월',
                            'YEARLY': '매년'
                        }.get(freq, freq)
                        
                        rec_text = f"{freq_korean}"
                        if interval and interval != '1':
                            rec_text += f" {interval}회"
                            
                        if until:
                            rec_text += f", 종료일: {until}"
                        elif count:
                            rec_text += f", {count}회 반복"
                            
                        ttk.Label(rec_frame, text=rec_text, style="SmallText.TLabel").pack(anchor="w", padx=5)
                    
                    # 반복 예외 날짜
                    exceptions = cal_analyser.get_exception_dates(event_id)
                    if exceptions:
                        ttk.Label(rec_frame, text="예외 날짜:", style="SmallText.TLabel").pack(anchor="w", padx=5, pady=(5, 0))
                        
                        exc_dates = []
                        for exc in exceptions:
                            exc_date = exc.get('date')
                            if isinstance(exc_date, datetime):
                                exc_dates.append(exc_date.strftime("%Y-%m-%d"))
                            else:
                                exc_dates.append(str(exc_date))
                                
                        ttk.Label(rec_frame, text=", ".join(exc_dates), 
                                style="SmallText.TLabel", wraplength=650).pack(anchor="w", padx=15)
                
                # 4. 참여자 정보
                participants = cal_analyser.get_participants(event_id)
                if participants:
                    part_frame = ttk.LabelFrame(forensic_content, text="참여자")
                    part_frame.pack(fill="x", pady=3)
                    
                    for part in participants:
                        email = part.get('email', '')
                        name = part.get('name', '')
                        role = part.get('role', '')
                        status = part.get('status', '')
                        
                        # 역할 한글화
                        role_korean = {
                            'ORGANIZER': '주최자',
                            'ATTENDEE': '참석자',
                            'OPTIONAL': '선택참석자'
                        }.get(role, role)
                        
                        # 상태 한글화
                        status_korean = {
                            'ACCEPTED': '수락',
                            'DECLINED': '거절',
                            'TENTATIVE': '미정',
                            'NEEDS-ACTION': '응답 대기'
                        }.get(status, status)
                        
                        part_text = email
                        if name:
                            part_text = f"{name} <{email}>"
                            
                        if role_korean:
                            part_text += f" ({role_korean}"
                            if status_korean:
                                part_text += f", {status_korean}"
                            part_text += ")"
                            
                        ttk.Label(part_frame, text=part_text, style="SmallText.TLabel").pack(anchor="w", padx=5)
                
                # 5. 위치 정보
                loc_id = event.get("location_id")
                if loc_id:
                    loc_info = cal_analyser.get_location_info(loc_id)
                    if loc_info:
                        loc_frame = ttk.LabelFrame(forensic_content, text="위치 상세")
                        loc_frame.pack(fill="x", pady=3)
                        
                        for loc in loc_info:
                            title = loc.get('title', '')
                            address = loc.get('address', '')
                            lat = loc.get('latitude', '')
                            lng = loc.get('longitude', '')
                            
                            if title:
                                ttk.Label(loc_frame, text=f"이름: {title}", style="SmallText.TLabel").pack(anchor="w", padx=5)
                            if address:
                                ttk.Label(loc_frame, text=f"주소: {address}", style="SmallText.TLabel").pack(anchor="w", padx=5)
                            if lat and lng:
                                ttk.Label(loc_frame, text=f"좌표: {lat}, {lng}", style="SmallText.TLabel").pack(anchor="w", padx=5)
                
                # 6. 알람 정보
                alarms = cal_analyser.get_alarms_for_event(event_id)
                if alarms:
                    alarm_frame = ttk.LabelFrame(forensic_content, text="알람")
                    alarm_frame.pack(fill="x", pady=3)
                    
                    for alarm in alarms:
                        trigger = alarm.get('trigger_date', '')
                        alarm_type = alarm.get('type', '')
                        
                        # 알람 타입 한글화
                        type_korean = {
                            'EMAIL': '이메일',
                            'ALERT': '알림',
                            'NOTIFICATION': '알림',
                            'SOUND': '소리'
                        }.get(alarm_type, alarm_type)
                        
                        # 트리거 시간 계산 (음수는 이벤트 전, 양수는 이벤트 후)
                        trigger_text = str(trigger)
                        if isinstance(trigger, int):
                            minutes = abs(trigger)
                            hours = minutes // 60
                            remaining_mins = minutes % 60
                            
                            if hours > 0:
                                trigger_text = f"{hours}시간"
                                if remaining_mins > 0:
                                    trigger_text += f" {remaining_mins}분"
                            else:
                                trigger_text = f"{minutes}분"
                                
                            trigger_text = f"이벤트 {'전' if trigger < 0 else '후'} {trigger_text}"
                            
                        alarm_text = f"{type_korean}: {trigger_text}"
                        ttk.Label(alarm_frame, text=alarm_text, style="SmallText.TLabel").pack(anchor="w", padx=5)
                
                # 7. 첨부파일 정보
                attachments = cal_analyser.get_attachments_for_event(event_id)
                if attachments:
                    attach_frame = ttk.LabelFrame(forensic_content, text="첨부파일")
                    attach_frame.pack(fill="x", pady=3)
                    
                    for i, att in enumerate(attachments):
                        filename = att.get('filename', '파일')
                        mime_type = att.get('mime_type', '')
                        size = att.get('file_size', 0)
                        
                        # 파일 크기 포맷팅
                        size_str = ""
                        if size:
                            if size < 1024:
                                size_str = f"{size} B"
                            elif size < 1024*1024:
                                size_str = f"{size/1024:.1f} KB"
                            else:
                                size_str = f"{size/(1024*1024):.1f} MB"
                                
                        attach_text = filename
                        if mime_type:
                            attach_text += f" ({mime_type})"
                        if size_str:
                            attach_text += f" - {size_str}"
                            
                        ttk.Label(attach_frame, text=attach_text, style="SmallText.TLabel").pack(anchor="w", padx=5)
            
            # 구분선 (마지막 이벤트 제외)
            if i < len(sorted_events) - 1:
                ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=8)
    
    def go_to_today():
        """달력을 오늘 날짜가 포함된 월로 이동합니다."""
        today = datetime.now()
        state.current_year = today.year
        state.current_month = today.month
        update_month_label()
        refresh_calendar()
    
    def change_month(delta):
        """
        월을 변경합니다.
        
        Args:
            delta: 변경할 월 수 (+1: 다음달, -1: 이전달)
        """
        new_month = state.current_month + delta
        new_year = state.current_year
        
        # 연도 넘김 처리
        if new_month < 1:
            new_month = 12
            new_year -= 1
        elif new_month > 12:
            new_month = 1
            new_year += 1
            
        state.current_year = new_year
        state.current_month = new_month
        update_month_label()
        refresh_calendar()
    
    # 최초 달력 표시
    refresh_calendar()
    
    # 상태바 (하단 정보)
    status_frame = ttk.Frame(parent_frame)
    status_frame.pack(fill="x", pady=5)
    
    # 이벤트 합계 표시 (좌측)
    event_count = len(state.events_cache.get(f"{state.current_year}-{state.current_month}", pd.DataFrame()))
    count_label = ttk.Label(status_frame, 
                          text=f"전체 이벤트: {event_count}개", 
                          style="SmallText.TLabel")
    count_label.pack(side="left")
    
    # 백업 경로 표시 (우측)
    path_label = ttk.Label(status_frame, 
                         text=f"백업 경로: {backup_path}", 
                         style="SmallText.TLabel")
    path_label.pack(side="right")