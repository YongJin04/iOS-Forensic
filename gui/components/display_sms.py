import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import os
import sys
import io
import re
import webbrowser
from PIL import Image, ImageTk
from datetime import datetime
import pandas as pd

# 백엔드 모듈 임포트
from artifact_analyzer.messenger.sms.sms_analyser import SMSAnalyser

def display_sms(parent_frame, backup_path):
    """SMS 메시지 데이터를 표시합니다."""
    # 기존 위젯 삭제
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # SMS 분석 헤더
    ttk.Label(parent_frame, text="SMS 메시지 분석", style="HeaderLarge.TLabel").pack(anchor="w", pady=(0, 10))
    
    # SMS 분석기 초기화
    try:
        sms_analyser = SMSAnalyser(backup_path)
        if not sms_analyser.connect_to_db():
            messagebox.showerror("오류", "SMS 데이터베이스를 찾을 수 없거나 연결할 수 없습니다.")
            ttk.Label(parent_frame, text="SMS 데이터베이스를 찾을 수 없거나 연결할 수 없습니다.", 
                      style="ErrorText.TLabel").pack(pady=20)
            return
    except Exception as e:
        messagebox.showerror("오류", f"SMS 분석기 초기화 중 오류가 발생했습니다: {str(e)}")
        ttk.Label(parent_frame, text=f"오류: {str(e)}", style="ErrorText.TLabel").pack(pady=20)
        return
    
    # 메인 프레임 설정
    main_frame = ttk.Frame(parent_frame)
    main_frame.pack(fill="both", expand=True)
    
    # 좌우 분할 프레임 (PanedWindow 사용)
    paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
    paned_window.pack(fill="both", expand=True)
    
    # 좌측 대화 목록 프레임
    contact_frame = ttk.Frame(paned_window, padding=10)
    paned_window.add(contact_frame, weight=1)
    
    # 우측 메시지 프레임
    message_frame = ttk.Frame(paned_window, padding=10)
    paned_window.add(message_frame, weight=3)
    
    # 대화 상대 목록
    ttk.Label(contact_frame, text="대화 상대 목록", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
    
    # 대화 상대 리스트박스
    contact_listbox = tk.Listbox(contact_frame, selectmode=tk.SINGLE)
    contact_listbox.pack(fill="both", expand=True)
    
    # 스크롤바 추가 (Listbox 위젯과 연결)
    scrollbar = ttk.Scrollbar(contact_listbox, orient="vertical", command=contact_listbox.yview)
    contact_listbox.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    
    # 현재 선택된 대화 상대 정보
    selected_conversation = {"handle_rowid": None, "handle_id": None}
    
    # 우측 프레임에 기본 메시지 표시
    message_placeholder = ttk.Label(message_frame, text="좌측 대화 상대 목록에서 선택하여 대화 내용을 확인하세요.",
                                   style="Text.TLabel")
    message_placeholder.pack(expand=True)
    
    # URL 감지 함수
    def detect_urls(text):
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
        return re.findall(url_pattern, text)
    
    # URL 클릭 핸들러
    def open_url(url):
        # www로 시작하면 http:// 추가
        if url.startswith('www.'):
            url = 'http://' + url
        webbrowser.open(url)
    
    # 하이퍼링크 텍스트 생성 함수
    def create_hyperlink_text(parent, message_text, bg_color, wraplength):
        # URL 패턴 찾기
        urls = detect_urls(message_text)
        
        if not urls:
            # URL이 없으면 일반 텍스트로 표시
            text_label = tk.Label(parent, text=message_text, justify=tk.LEFT,
                                wraplength=wraplength, bg=bg_color, padx=10, pady=10)
            text_label.pack(fill="both", expand=True)
            return
        
        # URL이 있으면 텍스트를 분할하여 표시
        text_frame = tk.Frame(parent, bg=bg_color, padx=10, pady=10)
        text_frame.pack(fill="both", expand=True)
        
        current_pos = 0
        for url in urls:
            # URL 전 텍스트 처리
            url_start = message_text.find(url, current_pos)
            if url_start > current_pos:
                pre_text = message_text[current_pos:url_start]
                tk.Label(text_frame, text=pre_text, justify=tk.LEFT, 
                        wraplength=wraplength, bg=bg_color).pack(anchor="w", pady=0)
            
            # URL 처리 (클릭 가능한 링크)
            link = tk.Label(text_frame, text=url, fg="blue", cursor="hand2", 
                           justify=tk.LEFT, wraplength=wraplength, bg=bg_color)
            link.pack(anchor="w", pady=0)
            link.bind("<Button-1>", lambda e, url=url: open_url(url))
            
            # 밑줄 효과 추가 (마우스 호버)
            def on_enter(e, label=link):
                label.config(font=('Helvetica', 10, 'underline'))
            
            def on_leave(e, label=link):
                label.config(font=('Helvetica', 10))
            
            link.bind("<Enter>", on_enter)
            link.bind("<Leave>", on_leave)
            
            current_pos = url_start + len(url)
        
        # 마지막 URL 이후 텍스트 처리
        if current_pos < len(message_text):
            post_text = message_text[current_pos:]
            tk.Label(text_frame, text=post_text, justify=tk.LEFT, 
                    wraplength=wraplength, bg=bg_color).pack(anchor="w", pady=0)
    
    # 대화 내용을 표시하는 함수
    def show_conversation(event=None):
        selection = contact_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        conversation_data = conversations[index]
        selected_conversation["handle_rowid"] = conversation_data["handle_rowid"]
        selected_conversation["handle_id"] = conversation_data["handle_id"]
        
        # 메시지 프레임 초기화
        for widget in message_frame.winfo_children():
            widget.destroy()
        
        # 대화 상대 정보 헤더
        header_frame = ttk.Frame(message_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(header_frame, text=f"대화 상대: {conversation_data['formatted_id']}", 
                 style="Header.TLabel").pack(side="left")
        
        # 메시지 표시 영역 (Canvas와 Scrollbar 사용)
        message_canvas = tk.Canvas(message_frame, bg="#f0f0f0")
        message_scrollbar = ttk.Scrollbar(message_frame, orient="vertical", command=message_canvas.yview)
        message_scroll_frame = ttk.Frame(message_canvas)
        
        # 동적으로 canvas scrollregion 갱신
        message_scroll_frame.bind(
            "<Configure>",
            lambda e: message_canvas.configure(scrollregion=message_canvas.bbox("all"))
        )
        
        message_canvas.create_window((0, 0), window=message_scroll_frame, anchor="nw")
        message_canvas.configure(yscrollcommand=message_scrollbar.set)
        
        message_canvas.pack(side="left", fill="both", expand=True)
        message_scrollbar.pack(side="right", fill="y")
        
        # 창 크기가 변경될 때 각 메시지 버블 내부의 내용을 갱신 (동적 비율 적용)
        def on_canvas_configure(event):
            new_width = event.width
            for child in message_scroll_frame.winfo_children():
                # 메시지 버블의 wraplength와 이미지 크기도 부모 너비에 맞춰 재조정
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Label) and subchild.cget("wraplength"):
                        subchild.config(wraplength=int(new_width * 0.7))
                    # 이미지가 포함된 라벨은 따로 갱신할 수 있습니다.
        message_canvas.bind("<Configure>", on_canvas_configure)
        
        # 메시지 데이터 가져오기
        messages = sms_analyser.get_conversation_messages(conversation_data["handle_rowid"])
        if not messages:
            ttk.Label(message_scroll_frame, text="메시지가 없습니다.", style="Text.TLabel").pack(pady=20)
            return
        
        # 각 메시지 표시
        for message in messages:
            create_message_bubble(message_scroll_frame, message, message_canvas)
        
        # 스크롤을 맨 아래로 이동
        message_canvas.update_idletasks()
        message_canvas.yview_moveto(1.0)
    
    # 메시지 버블 생성 함수 (동적 이미지 크기 적용)
    def create_message_bubble(parent, message, canvas):
        bubble_frame = ttk.Frame(parent, padding=5)
        bubble_frame.pack(fill="x", pady=5)
        
        # 발신/수신에 따라 정렬 변경
        if message["is_from_me"]:
            align_frame = ttk.Frame(bubble_frame)
            align_frame.pack(side="right", anchor="e")
            bubble_color = "#88B6FF"  # 발신 메시지 색상
        else:
            align_frame = ttk.Frame(bubble_frame)
            align_frame.pack(side="left", anchor="w")
            bubble_color = "#ECECEC"  # 수신 메시지 색상
        
        content_frame = ttk.Frame(align_frame, style="Card.TFrame", padding=10)
        content_frame.pack(fill="both")
        
        # 이미지나 텍스트 출력 영역 동적 너비 (canvas의 너비 정보를 참조)
        available_width = canvas.winfo_width() if canvas.winfo_width() > 0 else 300
        
        # 사진 메시지 처리: 동적 크기로 리사이즈
        if message.get("attachment_path"):
            try:
                if os.path.exists(message["attachment_path"]):
                    img = Image.open(message["attachment_path"])
                    # 이미지의 최대 폭을 available_width의 90%로 제한하고 비율 유지
                    max_img_width = int(available_width * 0.9)
                    ratio = max_img_width / img.width
                    new_size = (max_img_width, int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    img_label = ttk.Label(content_frame, image=photo)
                    img_label.image = photo  # 참조 유지
                    img_label.pack(pady=5)
                else:
                    ttk.Label(content_frame, text="[이미지를 찾을 수 없음]", style="Text.TLabel").pack(pady=5)
            except Exception as e:
                ttk.Label(content_frame, text=f"[이미지 로드 오류: {str(e)}]", style="Text.TLabel").pack(pady=5)
        else:
            message_text = message["text"]
            if message_text:
                # 텍스트에 URL이 있는지 확인하고 하이퍼링크로 처리
                create_hyperlink_text(content_frame, message_text, bubble_color, int(available_width * 0.7))
        
        ttk.Label(content_frame, text=message["date_str"], style="SmallText.TLabel").pack(pady=(5, 0))
    
    # 대화 목록 로드
    try:
        conversations = sms_analyser.get_conversations()
        if not conversations:
            ttk.Label(contact_frame, text="대화 상대가 없습니다.", style="Text.TLabel").pack(pady=20)
        else:
            for i, conversation in enumerate(conversations):
                contact_listbox.insert(tk.END, conversation["formatted_id"])
            
            # 대화 상대 선택 이벤트 연결
            contact_listbox.bind('<<ListboxSelect>>', show_conversation)
            
            # 전체 SMS 메시지 통계 및 표시
            all_messages_df = sms_analyser.get_all_sms_messages()
            stats = sms_analyser.get_sms_stats(all_messages_df)
            
            stats_frame = ttk.Frame(parent_frame, style="Card.TFrame", padding=10)
            stats_frame.pack(fill="x", pady=10)
            ttk.Label(stats_frame, 
                      text=f"통계: 총 {stats['total']}개 메시지 (발신: {stats['sent']}개, 수신: {stats['received']}개, 대화상대: {stats['contacts']}명)", 
                      style="Text.TLabel").pack(anchor="w")
    except Exception as e:
        messagebox.showerror("오류", f"대화 목록 로드 중 오류가 발생했습니다: {str(e)}")
        ttk.Label(contact_frame, text=f"오류: {str(e)}", style="ErrorText.TLabel").pack(pady=20)
    
    # 전체 SMS 보기 버튼
    def show_all_sms():
        for widget in message_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(message_frame, text="전체 SMS 목록", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        
        table_frame = ttk.Frame(message_frame)
        table_frame.pack(fill="both", expand=True)
        
        columns = ("번호", "날짜", "방향", "연락처", "내용")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)
        
        tree.heading("번호", text="번호")
        tree.heading("날짜", text="날짜")
        tree.heading("방향", text="방향")
        tree.heading("연락처", text="연락처")
        tree.heading("내용", text="내용")
        tree.column("번호", width=50, anchor="center")
        tree.column("날짜", width=150, anchor="center")
        tree.column("방향", width=50, anchor="center")
        tree.column("연락처", width=150, anchor="w")
        tree.column("내용", width=300, anchor="w")
        
        all_messages_df = sms_analyser.get_all_sms_messages()
        for _, row in all_messages_df.iterrows():
            tree.insert("", "end", values=(
                row['rowid'],
                row['date'].strftime('%Y-%m-%d %H:%M:%S'),
                row['direction'],
                row['formatted_contact'],
                row['text'] if pd.notna(row['text']) else ""
            ))
        
        detail_frame = ttk.Frame(message_frame, style="Card.TFrame", padding=10)
        detail_frame.pack(fill="x", pady=10)
        
        # 상세 보기 프레임
        detail_text_frame = ttk.Frame(detail_frame)
        detail_text_frame.pack(fill="x", expand=True)
        
        detail_label = ttk.Label(detail_text_frame, 
                               text="메시지를 선택하면 여기에 상세 내용이 표시됩니다.", 
                               style="Text.TLabel", wraplength=800)
        detail_label.pack(fill="x")
        
        # 하이퍼링크를 위한 상세 보기 프레임
        detail_content_frame = tk.Frame(detail_frame, bg=detail_frame.cget("background"))
        detail_content_frame.pack(fill="x", expand=True, pady=5)
        
        def show_selected_message(event):
            selected_item = tree.selection()
            if selected_item:
                item = tree.item(selected_item[0])
                message_content = item['values'][4]
                contact = item['values'][3]
                date = item['values'][1]
                direction = item['values'][2]
                
                # 기존 라벨 업데이트
                detail_label.config(text=f"날짜: {date}\n방향: {direction}\n연락처: {contact}\n")
                
                # 기존 상세 내용 위젯 제거
                for widget in detail_content_frame.winfo_children():
                    widget.destroy()
                
                # URL 포함 여부에 따라 처리
                if message_content and isinstance(message_content, str):
                    urls = detect_urls(message_content)
                    if urls:
                        # URL이 있으면 하이퍼링크로 처리
                        create_hyperlink_text(detail_content_frame, message_content, 
                                             detail_content_frame.cget("background"), 800)
                    else:
                        # URL이 없으면 일반 텍스트로 표시
                        tk.Label(detail_content_frame, text=message_content, 
                                justify=tk.LEFT, wraplength=800, 
                                bg=detail_content_frame.cget("background")).pack(fill="x")
        
        tree.bind("<<TreeviewSelect>>", show_selected_message)
    
    all_sms_button = ttk.Button(contact_frame, text="전체 SMS 목록 보기", command=show_all_sms)
    all_sms_button.pack(fill="x", pady=10)