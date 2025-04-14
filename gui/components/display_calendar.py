import tkinter as tk
from tkinter import ttk, messagebox
import calendar
from datetime import datetime, timedelta
import pandas as pd

# 백엔드 모듈 임포트 (포렌식 기능이 통합된 CalendarAnalyser)
from artifact_analyzer.calendar.calendar_analyzer import CalendarAnalyser

def display_calendar(parent_frame, backup_path):
    """창 크기에 맞춰 균등 확장되는 달력 UI.
       다중일정(여러 날짜)에 걸친 이벤트 표시 & 더블클릭 시 통합 상세 팝업(스크롤 포함)
    """
    # 기존 위젯 삭제
    for widget in parent_frame.winfo_children():
        widget.destroy()

    # 색상 문자열 정규화 함수: "#RRGGBBAA" → "#RRGGBB"
    def normalize_color(color_str):
        if isinstance(color_str, str) and len(color_str) == 9:
            return color_str[:7]
        return color_str or "#FFFFFF"

    # 스타일 설정
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("HeaderLarge.TLabel", font=("Helvetica", 18, "bold"), foreground="#2C3E50")
    style.configure("Header.TLabel", font=("Helvetica", 14, "bold"), foreground="#34495E")
    style.configure("HeaderSmall.TLabel", font=("Helvetica", 10, "bold"), foreground="#2980B9")
    style.configure("Text.TLabel", font=("Helvetica", 10), foreground="#2C3E50", background="white")
    style.configure("SmallText.TLabel", font=("Helvetica", 8), foreground="#7F8C8D")
    style.configure("TButton", font=("Helvetica", 10), padding=5)
    style.configure("Calendar.TFrame", background="#FDFDFD")

    # 헤더 (제목)
    header_label = ttk.Label(parent_frame, text="캘린더 분석", style="HeaderLarge.TLabel")
    header_label.pack(anchor="w", pady=(0, 10))

    # CalendarAnalyser 초기화
    try:
        cal_analyser = CalendarAnalyser(backup_path)
        if not cal_analyser.connect_to_db():
            messagebox.showerror("오류", "캘린더 DB를 찾을 수 없거나 연결할 수 없습니다.")
            ttk.Label(parent_frame, text="DB 연결 실패.", style="ErrorText.TLabel").pack(pady=20)
            return
    except Exception as e:
        messagebox.showerror("오류", f"분석기 초기화 오류: {str(e)}")
        return

    # 기본 날짜 설정 (오늘)
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month

    # 상단 네비게이션 영역
    nav_frame = ttk.Frame(parent_frame)
    nav_frame.pack(fill="x", pady=5)

    month_label_var = tk.StringVar()
    def update_month_label():
        month_label_var.set(f"{current_year}년 {current_month}월")
    update_month_label()

    ttk.Button(nav_frame, text="◀ 이전", command=lambda: change_month(-1)).pack(side="left")
    ttk.Label(nav_frame, textvariable=month_label_var, style="Header.TLabel").pack(side="left", padx=10)
    ttk.Button(nav_frame, text="다음 ▶", command=lambda: change_month(1)).pack(side="left")

    # 메인 달력 프레임
    calendar_frame = ttk.Frame(parent_frame, style="Calendar.TFrame")
    calendar_frame.pack(fill="both", expand=True, pady=10)

    # 동일한 셀 크기 보장을 위해 행과 열 weight 설정 (요일 헤더 포함 7행, 7열)
    for r in range(7):
        calendar_frame.rowconfigure(r, weight=1)
    for c in range(7):
        calendar_frame.columnconfigure(c, weight=1)

    events_df = None
    def load_events():
        nonlocal events_df
        events_df = cal_analyser.get_events_for_month(current_year, current_month)
        events_by_day = {}
        for _, event in events_df.iterrows():
            start_dt = event['start_date']
            end_dt = event['end_date'] if event['end_date'] else start_dt
            if not start_dt:
                continue
            curr_day = start_dt.date()
            end_day = end_dt.date()
            while curr_day <= end_day:
                if curr_day.month == current_month:
                    day_num = curr_day.day
                    events_by_day.setdefault(day_num, []).append(event)
                curr_day += timedelta(days=1)
        return events_by_day

    def refresh_calendar():
        for widget in calendar_frame.winfo_children():
            widget.destroy()
        events_by_day = load_events()

        # 요일 헤더 (row=0)
        days_of_week = ["월", "화", "수", "목", "금", "토", "일"]
        for col, day_name in enumerate(days_of_week):
            lbl = ttk.Label(calendar_frame, text=day_name, style="HeaderSmall.TLabel", anchor="center")
            lbl.grid(row=0, column=col, sticky="nsew", padx=2, pady=2)

        # 날짜 셀 (row=1 ~ 6)
        cal_obj = calendar.Calendar(firstweekday=0)
        month_weeks = cal_obj.monthdayscalendar(current_year, current_month)
        for row_idx, week in enumerate(month_weeks, start=1):
            for col_idx, day_num in enumerate(week):
                cell_frame = ttk.Frame(calendar_frame, borderwidth=1, relief="groove")
                cell_frame.grid(row=row_idx, column=col_idx, sticky="nsew", padx=2, pady=2)
                if day_num == 0:
                    continue
                lbl_day = ttk.Label(cell_frame, text=str(day_num), style="Header.TLabel", anchor="nw")
                lbl_day.pack(anchor="nw", padx=2, pady=2)
                if day_num in events_by_day:
                    for event in events_by_day[day_num]:
                        summary = event.get('summary') or "제목 없음"
                        bg_color = normalize_color(event.get('color'))
                        ev_label = tk.Label(cell_frame, text=summary, bg=bg_color,
                                            font=("Helvetica", 9), anchor="w", relief="groove")
                        ev_label.pack(fill="x", padx=2, pady=1)
                def on_double_click(e, day=day_num):
                    show_day_details(day)
                cell_frame.bind("<Double-1>", on_double_click)
                for child in cell_frame.winfo_children():
                    child.bind("<Double-1>", on_double_click)

    def show_day_details(day):
        """선택한 날짜의 이벤트 상세 정보를 스크롤 가능한 통합 팝업으로 표시합니다."""
        detail_window = tk.Toplevel(parent_frame)
        detail_window.title(f"{current_year}년 {current_month}월 {day}일 이벤트 상세")
        detail_window.geometry("700x500")

        # 스크롤 가능한 영역 구성: Canvas + Scrollbar + 내부 Frame
        canvas = tk.Canvas(detail_window, highlightthickness=0)
        scrollbar = ttk.Scrollbar(detail_window, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        content_frame = ttk.Frame(canvas, padding=10)
        canvas_window = canvas.create_window((0,0), window=content_frame, anchor="nw")

        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        content_frame.bind("<Configure>", on_configure)

        events_by_day = load_events()
        events = events_by_day.get(day, [])
        if not events:
            ttk.Label(content_frame, text="이 날짜에 이벤트가 없습니다.", style="Text.TLabel").pack(pady=20)
            return

        # 통합 이벤트 상세 카드 (하나의 프레임에 모든 정보를 표시)
        for event in events:
            evt_frame = ttk.Frame(content_frame, relief="groove", borderwidth=1, padding=8)
            evt_frame.pack(fill="x", pady=4)
            # 이벤트 기본 정보
            summary = event.get('summary') or "제목 없음"
            start_dt = event.get('start_date')
            end_dt = event.get('end_date')
            start_str = start_dt.strftime('%m/%d %H:%M') if start_dt else ""
            end_str = end_dt.strftime('%m/%d %H:%M') if end_dt else ""
            time_str = f"{start_str} ~ {end_str}" if end_dt else start_str
            header_text = f"{summary} ({time_str})"
            info_text = f"캘린더: {event.get('calendar_title','')}\n" \
                        f"색상: {event.get('color','')} / {event.get('symbolic_color_name','')}\n" \
                        f"설명: {event.get('description','')}\n" \
                        f"전체일정: {'예' if event.get('all_day') else '아니오'}"
            # 포렌식 분석 정보 통합
            forensic_parts = []
            evt_id = event.get("event_id")
            if evt_id:
                errors = cal_analyser.get_error_logs(evt_id)
                if errors:
                    err_str = "오류 로그: " + "; ".join([f"{err.get('error_type','')}: {err.get('error_code','')}({err.get('user_info','')})" for err in errors])
                    forensic_parts.append(err_str)
                actions = cal_analyser.get_event_actions(evt_id)
                if actions:
                    act_str = "외부 연동: " + "; ".join([f"ID:{act.get('external_id','')} Tag:{act.get('external_mod_tag','')}" for act in actions])
                    forensic_parts.append(act_str)
                exceptions = cal_analyser.get_exception_dates(evt_id)
                if exceptions:
                    exc_str = "예외 날짜: " + ", ".join([exc.get('date').strftime("%Y-%m-%d") if isinstance(exc.get('date'), datetime) else str(exc.get('date')) for exc in exceptions])
                    forensic_parts.append(exc_str)
                recurrences = cal_analyser.get_recurrence_info(evt_id)
                if recurrences:
                    rec_str = "반복 규칙: " + ", ".join([f"freq:{rec.get('frequency','')} interval:{rec.get('interval','')}" for rec in recurrences])
                    forensic_parts.append(rec_str)
                participants = cal_analyser.get_participants(evt_id)
                if participants:
                    part_str = "참여자: " + ", ".join([f"{p.get('email','')}({p.get('role','')})" for p in participants])
                    forensic_parts.append(part_str)
                loc_id = event.get("location_id")
                if loc_id:
                    loc_info = cal_analyser.get_location_info(loc_id)
                    if loc_info:
                        loc_str = "위치: " + ", ".join([f"{loc.get('title','')} ({loc.get('address','')})" for loc in loc_info])
                        forensic_parts.append(loc_str)
                alarms = cal_analyser.get_alarms_for_event(evt_id)
                if alarms:
                    alarm_str = "알람: " + ", ".join([f"Trigger:{a.get('trigger_date','')} Type:{a.get('type','')}" for a in alarms])
                    forensic_parts.append(alarm_str)
                attachments = cal_analyser.get_attachments_for_event(evt_id)
                if attachments:
                    attach_str = "첨부파일: " + ", ".join([f"{att.get('filename','파일')}" for att in attachments])
                    forensic_parts.append(attach_str)

            # 모든 정보를 하나의 통합 텍스트로 결합
            combined_text = info_text + "\n" + "\n".join(forensic_parts) if forensic_parts else info_text

            ttk.Label(evt_frame, text=header_text, style="Header.TLabel").pack(anchor="w")
            ttk.Label(evt_frame, text=combined_text, style="Text.TLabel", wraplength=680, justify="left").pack(anchor="w", pady=4)

    def change_month(delta):
        nonlocal current_year, current_month
        new_month = current_month + delta
        new_year = current_year
        if new_month < 1:
            new_month = 12
            new_year -= 1
        elif new_month > 12:
            new_month = 1
            new_year += 1
        current_year = new_year
        current_month = new_month
        update_month_label()
        refresh_calendar()

    refresh_calendar()