#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CallHistoryDB 분석 GUI 프론트엔드 모듈
 - CallHistory.storedata 파일을 로드하고 분석 결과를 표시하는 사용자 인터페이스
 - 백엔드 모델(callhistory_analyzer.py)과 연계하여 동작
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import calendar
from datetime import datetime
import pandas as pd
from functools import partial

# 백엔드 모델 모듈 임포트
from callhistory_analyzer import CallHistoryModel


def display_call_history(parent_frame, database_path=None):
    """
    iOS CallHistory.storedata 분석을 위한 responsive UI
    
    기능
    ----
    * 통화 기록 탭: ZCALLRECORD 테이블 데이터 표시 및 누락 레코드 분석
    * 메타 데이터 탭: Z_PRIMARYKEY 테이블 정보 표시
    * 편리한 파일 로드 및 데이터 탐색 기능
    """
    
    # 기존 위젯 클리어 (메모리 효율성)
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # ---------------- 상태 관리 클래스 ----------------
    
    class CallHistoryState:
        def __init__(self):
            self.model = CallHistoryModel()
            self.database_path = None
            self.is_connected = False
            
    state = CallHistoryState()
    
    # ---------------- 유틸리티 함수 ----------------
    
    def create_tooltip(widget, text):
        """위젯에 툴팁 추가"""
        tooltip = None
        
        def enter(event):
            nonlocal tooltip
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
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
    
    # ---------------- 스타일 설정 ----------------
    
    def setup_styles():
        style = ttk.Style()
        style.theme_use("clam")  # 기본 테마 사용
        
        # 헤더 및 텍스트 스타일
        style.configure("HeaderLarge.TLabel", font=("Helvetica", 18, "bold"), foreground="#2C3E50")
        style.configure("Header.TLabel", font=("Helvetica", 14, "bold"), foreground="#34495E")
        style.configure("HeaderSmall.TLabel", font=("Helvetica", 10, "bold"), foreground="#2980B9")
        style.configure("Text.TLabel", font=("Helvetica", 10), foreground="#2C3E50")
        style.configure("SmallText.TLabel", font=("Helvetica", 8), foreground="#7F8C8D")
        
        # 버튼 스타일
        style.configure("TButton", font=("Helvetica", 10), padding=5)
        
        # 테이블 스타일
        style.configure("Treeview", font=("Helvetica", 10))
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
        
        # 탭 스타일
        style.configure("TNotebook", background="#FDFDFD")
        style.configure("TNotebook.Tab", font=("Helvetica", 10), padding=[10, 2])
        
        # 프레임 스타일
        style.configure("TFrame", background="#FDFDFD")
        style.configure("InfoFrame.TFrame", relief="groove", borderwidth=1, padding=8)
        
        # 에러 텍스트 스타일
        style.configure("ErrorText.TLabel", font=("Helvetica", 12), foreground="red")
        
    setup_styles()
    
    # ---------------- 헤더 / 타이틀 ----------------
    
    header_frame = ttk.Frame(parent_frame)
    header_frame.pack(fill="x", pady=(0, 5))
    
    header_label = ttk.Label(header_frame, text="iOS 통화 기록 분석 도구", style="HeaderLarge.TLabel")
    header_label.pack(side="left", pady=(0, 5))
    
    # ---------------- 데이터베이스 로드 섹션 ----------------
    
    load_frame = ttk.Frame(parent_frame)
    load_frame.pack(fill="x", pady=5)
    
    load_button = ttk.Button(
        load_frame, 
        text="CallHistory.storedata 파일 로드", 
        command=lambda: load_database()
    )
    load_button.pack(side="left")
    create_tooltip(load_button, "iOS 백업에서 추출한 CallHistory.storedata 파일 선택")
    
    path_var = tk.StringVar()
    path_var.set("파일을 로드하세요.")
    path_label = ttk.Label(load_frame, textvariable=path_var, style="SmallText.TLabel")
    path_label.pack(side="left", padx=10)
    
    # ---------------- 탭 컨테이너 ----------------
    
    tabs = ttk.Notebook(parent_frame)
    tabs.pack(fill="both", expand=True, pady=10)
    
    # 첫 번째 탭: 통화 기록 데이터
    main_tab = ttk.Frame(tabs)
    tabs.add(main_tab, text="통화 기록 분석")
    
    # 두 번째 탭: 메타 데이터
    meta_tab = ttk.Frame(tabs)
    tabs.add(meta_tab, text="메타 데이터 분석")
    
    # ---------------- 통화 기록 탭 내용 ----------------
    
    main_control_frame = ttk.Frame(main_tab)
    main_control_frame.pack(fill="x", pady=5)
    
    analyze_missing_button = ttk.Button(
        main_control_frame, 
        text="누락된 레코드 분석", 
        command=lambda: analyze_missing_records(),
        state="disabled"
    )
    analyze_missing_button.pack(side="left")
    create_tooltip(analyze_missing_button, "ZCALLRECORD 테이블의 누락 여부 분석")
    
    # 상태 메시지
    main_status_var = tk.StringVar()
    main_status_var.set("파일을 로드하세요.")
    main_status = ttk.Label(main_control_frame, textvariable=main_status_var, style="SmallText.TLabel")
    main_status.pack(side="right")
    
    # 통화 기록 테이블 (Treeview 사용)
    main_tree_frame = ttk.Frame(main_tab)
    main_tree_frame.pack(fill="both", expand=True, pady=5)
    
    # 스크롤바
    main_y_scroll = ttk.Scrollbar(main_tree_frame, orient="vertical")
    main_x_scroll = ttk.Scrollbar(main_tree_frame, orient="horizontal")
    
    # 트리뷰 테이블
    main_tree = ttk.Treeview(
        main_tree_frame,
        columns=("pk", "raw_zdate", "call_date", "duration", "address", "direction", "answered"),
        show="headings",
        yscrollcommand=main_y_scroll.set,
        xscrollcommand=main_x_scroll.set
    )
    
    # 컬럼 설정
    main_tree.heading("pk", text="PK")
    main_tree.heading("raw_zdate", text="Raw ZDATE")
    main_tree.heading("call_date", text="Call Date (kr)")
    main_tree.heading("duration", text="통화 시간(초)")
    main_tree.heading("address", text="전화번호")
    main_tree.heading("direction", text="방향")
    main_tree.heading("answered", text="Answered")
    
    # 컬럼 너비 설정
    main_tree.column("pk", width=50, anchor="center")
    main_tree.column("raw_zdate", width=120, anchor="center")
    main_tree.column("call_date", width=150, anchor="center")
    main_tree.column("duration", width=80, anchor="center")
    main_tree.column("address", width=120, anchor="center")
    main_tree.column("direction", width=70, anchor="center")
    main_tree.column("answered", width=70, anchor="center")
    
    # 스크롤바 설정
    main_y_scroll.config(command=main_tree.yview)
    main_x_scroll.config(command=main_tree.xview)
    
    # 배치
    main_y_scroll.pack(side="right", fill="y")
    main_x_scroll.pack(side="bottom", fill="x")
    main_tree.pack(side="left", fill="both", expand=True)
    
    # 항목 선택 시 상세 정보 표시 바인딩
    main_tree.bind("<<TreeviewSelect>>", lambda e: show_call_details())
    
    # 상세 정보 프레임
    detail_frame = ttk.LabelFrame(main_tab, text="통화 상세 정보")
    detail_frame.pack(fill="x", expand=False, pady=5, padx=5)
    
    detail_content = ttk.Frame(detail_frame, padding=5)
    detail_content.pack(fill="x", expand=True)
    
    # 상세 정보 필드 초기화
    detail_labels = {}
    detail_fields = ["전화번호", "통화일시", "통화시간", "통화유형", "착신/발신", "비고"]
    
    for i, field in enumerate(detail_fields):
        row = i // 3
        col = i % 3
        
        field_frame = ttk.Frame(detail_content)
        field_frame.grid(row=row, column=col, sticky="w", padx=10, pady=3)
        
        ttk.Label(field_frame, text=f"{field}:", style="HeaderSmall.TLabel").pack(side="left")
        detail_labels[field] = ttk.Label(field_frame, text="", style="Text.TLabel")
        detail_labels[field].pack(side="left", padx=5)
    
    # ---------------- 메타 데이터 탭 내용 ----------------
    
    meta_control_frame = ttk.Frame(meta_tab)
    meta_control_frame.pack(fill="x", pady=5)
    
    load_meta_button = ttk.Button(
        meta_control_frame, 
        text="Z_PRIMARYKEY 테이블 로드", 
        command=lambda: load_primarykey_info(),
        state="disabled"
    )
    load_meta_button.pack(side="left")
    create_tooltip(load_meta_button, "Z_PRIMARYKEY 테이블 메타데이터 로드")
    
    # 상태 메시지
    meta_status_var = tk.StringVar()
    meta_status_var.set("메타 데이터를 보려면 먼저 파일을 로드하세요.")
    meta_status = ttk.Label(meta_control_frame, textvariable=meta_status_var, style="SmallText.TLabel")
    meta_status.pack(side="right")
    
    # 메타 데이터 테이블 (Treeview 사용)
    meta_tree_frame = ttk.Frame(meta_tab)
    meta_tree_frame.pack(fill="both", expand=True, pady=5)
    
    # 스크롤바
    meta_y_scroll = ttk.Scrollbar(meta_tree_frame, orient="vertical")
    
    # 트리뷰 테이블
    meta_tree = ttk.Treeview(
        meta_tree_frame,
        columns=("entity", "max_pk"),
        show="headings",
        yscrollcommand=meta_y_scroll.set
    )
    
    # 컬럼 설정
    meta_tree.heading("entity", text="엔티티 이름")
    meta_tree.heading("max_pk", text="최대 PK (Z_MAX)")
    
    # 컬럼 너비 설정
    meta_tree.column("entity", width=250)
    meta_tree.column("max_pk", width=100, anchor="center")
    
    # 스크롤바 설정
    meta_y_scroll.config(command=meta_tree.yview)
    
    # 배치
    meta_y_scroll.pack(side="right", fill="y")
    meta_tree.pack(side="left", fill="both", expand=True)
    
    # ---------------- 데이터 조작 함수 ----------------
    
    def load_database(file_path=None):
        """
        파일 다이얼로그를 통해 CallHistory.storedata 파일을 선택하고,
        백엔드 모델을 통해 데이터베이스에 연결합니다.
        """
        if not file_path:
            file_path = filedialog.askopenfilename(
                title="CallHistory.storedata 파일 선택",
                filetypes=[("SQLite Files", "*.storedata *.db"), ("All Files", "*")]
            )
        
        if file_path:
            try:
                # 백엔드 모델을 통해 데이터베이스에 연결
                if state.model.connect_database(file_path):
                    state.database_path = file_path
                    state.is_connected = True
                    
                    # 경로 표시 업데이트
                    path_var.set(f"로드된 파일: {file_path}")
                    
                    # 버튼 활성화
                    analyze_missing_button.config(state="normal")
                    load_meta_button.config(state="normal")
                    
                    # 통화 기록 데이터 로드 및 표시
                    load_call_records()
                    
                    # 메타 데이터 상태 업데이트
                    meta_status_var.set("메타 데이터를 로드하려면 버튼을 클릭하세요.")
                else:
                    messagebox.showerror("오류", "데이터베이스 연결에 실패했습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"데이터베이스 연결 중 예외 발생: {str(e)}")
    
    def load_call_records():
        """
        백엔드 모델을 통해 ZCALLRECORD 테이블의 데이터를 로드하고 표시합니다.
        """
        try:
            # 테이블 초기화
            for item in main_tree.get_children():
                main_tree.delete(item)
                
            # 백엔드 모델로부터 통화 기록 데이터 가져오기
            records = state.model.get_call_records()
            
            # 표시할 데이터 가공 (날짜 형식 변환 포함)
            for record in records:
                pk, raw_zdate, duration, address, direction, answered = record
                
                # 날짜 변환 (백엔드 모델 함수 사용)
                call_date_local = state.model.format_korean_date(raw_zdate)
                
                # 트리뷰에 항목 추가
                main_tree.insert(
                    "", 
                    "end", 
                    values=(pk, raw_zdate, call_date_local, duration, address, direction, answered)
                )
                
            main_status_var.set(f"ZCALLRECORD 레코드 {len(records)}건 로드됨.")
        except Exception as e:
            messagebox.showerror("오류", f"데이터 로드 중 오류 발생: {str(e)}")
    
    def analyze_missing_records():
        """
        백엔드 모델을 통해 누락된(삭제된) 레코드를 분석하고 결과를 표시합니다.
        """
        try:
            # 백엔드 모델의 분석 함수 호출
            max_pk, count_records, missing_count = state.model.analyze_missing_records()
            
            missing_info = (
                f"ZCALLRECORD 테이블의 최대 PK 값: {max_pk}\n"
                f"실제 레코드 수: {count_records}\n"
                f"누락(삭제)된 레코드 수: {missing_count}"
            )
            
            # 결과 표시
            missing_window = tk.Toplevel(parent_frame)
            missing_window.title("누락된 레코드 분석 결과")
            missing_window.geometry("400x200")
            missing_window.transient(parent_frame)
            missing_window.grab_set()
            
            result_frame = ttk.Frame(missing_window, padding=20)
            result_frame.pack(fill="both", expand=True)
            
            ttk.Label(
                result_frame, 
                text="통화 기록 누락 분석 결과", 
                style="HeaderLarge.TLabel"
            ).pack(pady=(0, 20))
            
            ttk.Label(
                result_frame,
                text=missing_info,
                style="Text.TLabel"
            ).pack(fill="x", pady=10)
            
            ttk.Button(
                result_frame,
                text="확인",
                command=missing_window.destroy
            ).pack(pady=20)
            
        except Exception as e:
            messagebox.showerror("오류", f"누락 레코드 분석 중 오류 발생: {str(e)}")
    
    def load_primarykey_info():
        """
        백엔드 모델을 통해 Z_PRIMARYKEY 테이블의 메타데이터를 로드하고 표시합니다.
        """
        try:
            # 테이블 초기화
            for item in meta_tree.get_children():
                meta_tree.delete(item)
                
            # 백엔드 모델로부터 메타데이터 가져오기
            records = state.model.get_primarykey_info()
            
            # 트리뷰에 항목 추가
            for entity_name, max_pk in records:
                meta_tree.insert("", "end", values=(entity_name, max_pk))
                
            meta_status_var.set(f"Z_PRIMARYKEY 테이블의 엔티티 수: {len(records)}건 로드됨.")
        except Exception as e:
            messagebox.showerror("오류", f"메타 데이터 로드 중 오류 발생: {str(e)}")
    
    def show_call_details():
        """
        선택한 통화 기록의 상세 정보를 표시합니다.
        """
        selected = main_tree.selection()
        if not selected:
            return
            
        # 선택한 항목의 데이터 가져오기
        values = main_tree.item(selected[0], "values")
        if not values or len(values) < 7:
            return
            
        pk, raw_zdate, call_date, duration, address, direction, answered = values
        
        # 방향 텍스트 변환
        direction_text = "발신" if direction == "1" else "착신"
        
        # 응답 여부 텍스트 변환
        answered_text = "응답" if answered == "1" else "부재중"
        
        # 상세 정보 표시
        detail_labels["전화번호"].config(text=address)
        detail_labels["통화일시"].config(text=call_date)
        detail_labels["통화시간"].config(text=f"{duration}초")
        detail_labels["통화유형"].config(text=answered_text)
        detail_labels["착신/발신"].config(text=direction_text)
        detail_labels["비고"].config(text=f"PK: {pk}")
        
    # 데이터베이스 경로가 제공된 경우 자동으로 로드
    if database_path:
        load_database(database_path)
        
    # 종료 시 연결 닫기
    parent_frame.winfo_toplevel().protocol("WM_DELETE_WINDOW", lambda: close_application())
    
    def close_application():
        """애플리케이션 종료 시 데이터베이스 연결을 닫습니다."""
        if state.is_connected:
            state.model.close_connection()
        parent_frame.winfo_toplevel().destroy()


# 독립 실행을 위한 코드
if __name__ == '__main__':
    root = tk.Tk()
    root.title("iOS 통화 기록 분석 도구")
    root.geometry("900x600")
    
    main_frame = ttk.Frame(root)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    display_call_history(main_frame)
    
    root.mainloop()