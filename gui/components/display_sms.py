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

# 백엔드 모듈(SMS 분석 기능)을 임포트합니다.
from artifact_analyzer.messenger.sms.sms_analyser import SMSAnalyser

def display_sms(parent_frame, backup_path):
    """SMS 메시지 데이터를 표시하는 함수입니다.
    
    인자:
      parent_frame: SMS 데이터를 출력할 부모 위젯(프레임)
      backup_path: iOS 백업 파일의 경로 (SMS 데이터베이스를 찾기 위해 사용)
    """
    
    # 부모 프레임 내의 기존 위젯들을 모두 제거하여 초기 상태로 만듭니다.
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # 최상단에 'SMS 메시지 분석' 헤더를 추가합니다.
    ttk.Label(parent_frame, text="SMS 메시지 분석", style="HeaderLarge.TLabel").pack(anchor="w", pady=(0, 10))
    
    # 백엔드의 SMSAnalyser 클래스를 이용해 SMS 분석기를 초기화합니다.
    try:
        sms_analyser = SMSAnalyser(backup_path)
        # SMS 데이터베이스에 연결 시도. 실패할 경우 에러 메시지 출력 후 함수 종료.
        if not sms_analyser.connect_to_db():
            messagebox.showerror("오류", "SMS 데이터베이스를 찾을 수 없거나 연결할 수 없습니다.")
            ttk.Label(parent_frame, text="SMS 데이터베이스를 찾을 수 없거나 연결할 수 없습니다.", 
                      style="ErrorText.TLabel").pack(pady=20)
            return
    except Exception as e:
        # 초기화 과정에서 예외 발생 시 에러 메시지 출력 후 함수 종료.
        messagebox.showerror("오류", f"SMS 분석기 초기화 중 오류가 발생했습니다: {str(e)}")
        ttk.Label(parent_frame, text=f"오류: {str(e)}", style="ErrorText.TLabel").pack(pady=20)
        return
    
    # 메인 프레임을 생성하여 전체 레이아웃을 구성합니다.
    main_frame = ttk.Frame(parent_frame)
    main_frame.pack(fill="both", expand=True)
    
    # 좌우 분할을 위해 PanedWindow를 사용합니다.
    paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
    paned_window.pack(fill="both", expand=True)
    
    # 좌측: 대화 상대 목록을 표시할 프레임 생성
    contact_frame = ttk.Frame(paned_window, padding=10)
    paned_window.add(contact_frame, weight=1)
    
    # 우측: 선택된 대화의 메시지 내용을 표시할 프레임 생성
    message_frame = ttk.Frame(paned_window, padding=10)
    paned_window.add(message_frame, weight=3)
    
    # 좌측 프레임 상단에 대화 상대 목록 제목을 표시합니다.
    ttk.Label(contact_frame, text="대화 상대 목록", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
    
    # 대화 상대를 선택할 수 있도록 Listbox 위젯 생성 및 배치
    contact_listbox = tk.Listbox(contact_frame, selectmode=tk.SINGLE)
    contact_listbox.pack(fill="both", expand=True)
    
    # Listbox에 스크롤바 추가: 목록이 길 경우 스크롤 가능하도록 함
    scrollbar = ttk.Scrollbar(contact_listbox, orient="vertical", command=contact_listbox.yview)
    contact_listbox.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    
    # 현재 선택된 대화 상대의 정보를 저장할 변수 (handle_rowid와 handle_id)
    selected_conversation = {"handle_rowid": None, "handle_id": None}
    
    # 우측 프레임에 기본 메시지(안내 메시지)를 표시합니다.
    message_placeholder = ttk.Label(message_frame, text="좌측 대화 상대 목록에서 선택하여 대화 내용을 확인하세요.",
                                   style="Text.TLabel")
    message_placeholder.pack(expand=True)
    
    # --------------------------
    # URL 관련 함수 정의
    # --------------------------
    
    # 문자열 내 URL을 정규표현식을 사용하여 찾아내는 함수입니다.
    def detect_urls(text):
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
        return re.findall(url_pattern, text)
    
    # URL 클릭 시 웹 브라우저에서 해당 URL을 열어주는 핸들러 함수입니다.
    def open_url(url):
        # 'www.'로 시작하는 경우 http:// 를 추가합니다.
        if url.startswith('www.'):
            url = 'http://' + url
        webbrowser.open(url)
    
    # 텍스트 내 URL을 하이퍼링크 형식으로 변환하여 출력하는 함수입니다.
    def create_hyperlink_text(parent, message_text, bg_color, wraplength):
        # 텍스트에서 URL 패턴을 찾아 리스트로 반환합니다.
        urls = detect_urls(message_text)
        
        # URL이 없으면 일반 텍스트로 라벨 생성
        if not urls:
            text_label = tk.Label(parent, text=message_text, justify=tk.LEFT,
                                wraplength=wraplength, bg=bg_color, padx=10, pady=10)
            text_label.pack(fill="both", expand=True)
            return
        
        # URL이 포함되어 있으면 별도의 프레임에 텍스트를 분할하여 표시
        text_frame = tk.Frame(parent, bg=bg_color, padx=10, pady=10)
        text_frame.pack(fill="both", expand=True)
        
        current_pos = 0
        # URL이 포함된 부분을 찾아 각각 처리합니다.
        for url in urls:
            # URL 전의 텍스트 처리
            url_start = message_text.find(url, current_pos)
            if url_start > current_pos:
                pre_text = message_text[current_pos:url_start]
                tk.Label(text_frame, text=pre_text, justify=tk.LEFT, 
                        wraplength=wraplength, bg=bg_color).pack(anchor="w", pady=0)
            
            # URL 부분을 클릭 가능한 링크로 생성
            link = tk.Label(text_frame, text=url, fg="blue", cursor="hand2", 
                           justify=tk.LEFT, wraplength=wraplength, bg=bg_color)
            link.pack(anchor="w", pady=0)
            link.bind("<Button-1>", lambda e, url=url: open_url(url))
            
            # 마우스 오버 시 밑줄 효과를 주는 함수들을 정의합니다.
            def on_enter(e, label=link):
                label.config(font=('Helvetica', 10, 'underline'))
            
            def on_leave(e, label=link):
                label.config(font=('Helvetica', 10))
            
            link.bind("<Enter>", on_enter)
            link.bind("<Leave>", on_leave)
            
            # 현재 위치를 URL 끝으로 업데이트
            current_pos = url_start + len(url)
        
        # 마지막 URL 이후의 텍스트가 있다면 추가로 라벨을 생성
        if current_pos < len(message_text):
            post_text = message_text[current_pos:]
            tk.Label(text_frame, text=post_text, justify=tk.LEFT, 
                    wraplength=wraplength, bg=bg_color).pack(anchor="w", pady=0)
    
    # --------------------------
    # 대화 내용 표시 관련 함수 정의
    # --------------------------
    
    # 좌측 목록에서 대화 상대를 선택했을 때 호출되는 함수입니다.
    def show_conversation(event=None):
        # Listbox에서 선택된 인덱스를 가져옵니다.
        selection = contact_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        # 선택된 대화 상대에 대한 정보를 가져와 저장합니다.
        conversation_data = conversations[index]
        selected_conversation["handle_rowid"] = conversation_data["handle_rowid"]
        selected_conversation["handle_id"] = conversation_data["handle_id"]
        
        # 우측 메시지 프레임을 초기화(이전 내용 삭제)
        for widget in message_frame.winfo_children():
            widget.destroy()
        
        # 대화 상대의 정보를 헤더로 표시
        header_frame = ttk.Frame(message_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(header_frame, text=f"대화 상대: {conversation_data['formatted_id']}", 
                 style="Header.TLabel").pack(side="left")
        
        # 메시지 내용을 표시할 영역: Canvas와 스크롤바를 사용해 동적으로 메시지 표시
        message_canvas = tk.Canvas(message_frame, bg="#f0f0f0")
        message_scrollbar = ttk.Scrollbar(message_frame, orient="vertical", command=message_canvas.yview)
        message_scroll_frame = ttk.Frame(message_canvas)
        
        # 메시지 영역의 크기 변화에 따라 scrollregion을 업데이트합니다.
        message_scroll_frame.bind(
            "<Configure>",
            lambda e: message_canvas.configure(scrollregion=message_canvas.bbox("all"))
        )
        
        # Canvas 내에 메시지 프레임을 윈도우 형태로 생성
        message_canvas.create_window((0, 0), window=message_scroll_frame, anchor="nw")
        message_canvas.configure(yscrollcommand=message_scrollbar.set)
        
        # Canvas와 스크롤바 배치
        message_canvas.pack(side="left", fill="both", expand=True)
        message_scrollbar.pack(side="right", fill="y")
        
        # 창 크기 변화에 따라 메시지 버블 내 텍스트와 이미지 크기를 동적으로 조절합니다.
        def on_canvas_configure(event):
            new_width = event.width
            for child in message_scroll_frame.winfo_children():
                # 자식 위젯(메시지 버블)의 라벨 텍스트의 wraplength를 조정
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Label) and subchild.cget("wraplength"):
                        subchild.config(wraplength=int(new_width * 0.7))
        message_canvas.bind("<Configure>", on_canvas_configure)
        
        # 선택된 대화 상대의 메시지 데이터를 가져옵니다.
        messages = sms_analyser.get_conversation_messages(conversation_data["handle_rowid"])
        if not messages:
            ttk.Label(message_scroll_frame, text="메시지가 없습니다.", style="Text.TLabel").pack(pady=20)
            return
        
        # 각 메시지를 메시지 버블 형태로 출력합니다.
        for message in messages:
            create_message_bubble(message_scroll_frame, message, message_canvas)
        
        # 스크롤바를 맨 아래로 이동시켜 최신 메시지가 보이도록 함
        message_canvas.update_idletasks()
        message_canvas.yview_moveto(1.0)
    
    # 메시지 하나를 버블 형태로 생성하는 함수입니다.
    def create_message_bubble(parent, message, canvas):
        # 메시지 버블을 담을 프레임 생성 및 간격 설정
        bubble_frame = ttk.Frame(parent, padding=5)
        bubble_frame.pack(fill="x", pady=5)
        
        # 메시지가 발신(내 메시지)인지 수신(상대 메시지)인지에 따라 정렬 및 배경색 설정
        if message["is_from_me"]:
            align_frame = ttk.Frame(bubble_frame)
            align_frame.pack(side="right", anchor="e")
            bubble_color = "#88B6FF"  # 발신 메시지의 배경 색상
        else:
            align_frame = ttk.Frame(bubble_frame)
            align_frame.pack(side="left", anchor="w")
            bubble_color = "#ECECEC"  # 수신 메시지의 배경 색상
        
        # 메시지 내용(텍스트, 이미지 등)을 담을 카드 형태의 프레임 생성
        content_frame = ttk.Frame(align_frame, style="Card.TFrame", padding=10)
        content_frame.pack(fill="both")
        
        # Canvas의 너비 정보를 참조하여 메시지 버블 내 내용의 최대 너비 결정
        available_width = canvas.winfo_width() if canvas.winfo_width() > 0 else 300
        
        # 메시지가 첨부파일(예: 사진)을 포함하는 경우 처리
        if message.get("attachment_path"):
            try:
                if os.path.exists(message["attachment_path"]):
                    # 첨부 이미지 파일을 열고, 최대 너비의 90%로 리사이즈 (비율 유지)
                    img = Image.open(message["attachment_path"])
                    max_img_width = int(available_width * 0.9)
                    ratio = max_img_width / img.width
                    new_size = (max_img_width, int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    img_label = ttk.Label(content_frame, image=photo)
                    img_label.image = photo  # 가비지 컬렉션 방지를 위해 참조 유지
                    img_label.pack(pady=5)
                else:
                    # 파일이 존재하지 않는 경우 메시지 출력
                    ttk.Label(content_frame, text="[이미지를 찾을 수 없음]", style="Text.TLabel").pack(pady=5)
            except Exception as e:
                # 이미지 로드 중 예외 발생 시 에러 메시지 출력
                ttk.Label(content_frame, text=f"[이미지 로드 오류: {str(e)}]", style="Text.TLabel").pack(pady=5)
        else:
            # 첨부파일이 없으면 메시지 텍스트를 처리
            message_text = message["text"]
            if message_text:
                # 텍스트 내 URL을 감지하여 하이퍼링크 처리 후 출력
                create_hyperlink_text(content_frame, message_text, bubble_color, int(available_width * 0.7))
        
        # 메시지 날짜 정보를 하단에 출력
        ttk.Label(content_frame, text=message["date_str"], style="SmallText.TLabel").pack(pady=(5, 0))
    
    # --------------------------
    # 대화 목록 및 통계 정보 로드
    # --------------------------
    
    try:
        # 백엔드에서 대화 목록을 불러옵니다.
        conversations = sms_analyser.get_conversations()
        if not conversations:
            # 대화 상대가 없을 경우 안내 메시지 표시
            ttk.Label(contact_frame, text="대화 상대가 없습니다.", style="Text.TLabel").pack(pady=20)
        else:
            # 각 대화 상대를 Listbox에 추가 (전화번호 형식 적용)
            for i, conversation in enumerate(conversations):
                contact_listbox.insert(tk.END, conversation["formatted_id"])
            
            # Listbox에서 대화 상대를 선택했을 때 show_conversation 함수가 호출되도록 이벤트 연결
            contact_listbox.bind('<<ListboxSelect>>', show_conversation)
            
            # 전체 SMS 메시지를 DataFrame으로 불러와 통계 정보를 계산 후 표시
            all_messages_df = sms_analyser.get_all_sms_messages()
            stats = sms_analyser.get_sms_stats(all_messages_df)
            
            # 통계 정보를 표시할 프레임 생성 및 내용 추가
            stats_frame = ttk.Frame(parent_frame, style="Card.TFrame", padding=10)
            stats_frame.pack(fill="x", pady=10)
            ttk.Label(stats_frame, 
                      text=f"통계: 총 {stats['total']}개 메시지 (발신: {stats['sent']}개, 수신: {stats['received']}개, 대화상대: {stats['contacts']}명)", 
                      style="Text.TLabel").pack(anchor="w")
    except Exception as e:
        # 대화 목록 로드 도중 에러 발생 시 에러 메시지 출력
        messagebox.showerror("오류", f"대화 목록 로드 중 오류가 발생했습니다: {str(e)}")
        ttk.Label(contact_frame, text=f"오류: {str(e)}", style="ErrorText.TLabel").pack(pady=20)
    
    # --------------------------
    # '전체 SMS 목록 보기' 버튼 및 관련 기능
    # --------------------------
    
    # 전체 SMS 메시지를 테이블 형식으로 출력하는 함수입니다.
    def show_all_sms():
        # 우측 메시지 프레임 초기화
        for widget in message_frame.winfo_children():
            widget.destroy()
        
        # 제목 라벨 추가
        ttk.Label(message_frame, text="전체 SMS 목록", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        
        # 테이블을 담을 프레임 생성
        table_frame = ttk.Frame(message_frame)
        table_frame.pack(fill="both", expand=True)
        
        # Treeview를 사용해 테이블 형태의 SMS 목록을 구성
        columns = ("번호", "날짜", "방향", "연락처", "내용")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)
        
        # 각 열의 제목과 너비, 정렬을 설정합니다.
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
        
        # 전체 SMS 메시지를 DataFrame으로 가져와서 Treeview에 추가
        all_messages_df = sms_analyser.get_all_sms_messages()
        for _, row in all_messages_df.iterrows():
            tree.insert("", "end", values=(
                row['rowid'],
                row['date'].strftime('%Y-%m-%d %H:%M:%S'),
                row['direction'],
                row['formatted_contact'],
                row['text'] if pd.notna(row['text']) else ""
            ))
        
        # 하단에 메시지 상세 정보를 표시할 프레임 생성
        detail_frame = ttk.Frame(message_frame, style="Card.TFrame", padding=10)
        detail_frame.pack(fill="x", pady=10)
        
        # 상세 정보를 위한 텍스트 라벨과 컨텐츠 프레임 생성
        detail_text_frame = ttk.Frame(detail_frame)
        detail_text_frame.pack(fill="x", expand=True)
        
        detail_label = ttk.Label(detail_text_frame, 
                               text="메시지를 선택하면 여기에 상세 내용이 표시됩니다.", 
                               style="Text.TLabel", wraplength=800)
        detail_label.pack(fill="x")
        
        # 하이퍼링크 포함 가능성을 고려한 상세 내용 표시 프레임
        detail_content_frame = tk.Frame(detail_frame, bg=detail_frame.cget("background"))
        detail_content_frame.pack(fill="x", expand=True, pady=5)
        
        # Treeview에서 메시지 선택 시 상세 내용을 업데이트하는 함수입니다.
        def show_selected_message(event):
            selected_item = tree.selection()
            if selected_item:
                item = tree.item(selected_item[0])
                message_content = item['values'][4]
                contact = item['values'][3]
                date = item['values'][1]
                direction = item['values'][2]
                
                # 상세 정보 라벨에 날짜, 방향, 연락처 정보를 업데이트
                detail_label.config(text=f"날짜: {date}\n방향: {direction}\n연락처: {contact}\n")
                
                # 기존 상세 내용 위젯을 모두 제거
                for widget in detail_content_frame.winfo_children():
                    widget.destroy()
                
                # 메시지 내용에 URL이 포함되어 있으면 하이퍼링크 처리, 아니면 일반 텍스트로 표시
                if message_content and isinstance(message_content, str):
                    urls = detect_urls(message_content)
                    if urls:
                        create_hyperlink_text(detail_content_frame, message_content, 
                                             detail_content_frame.cget("background"), 800)
                    else:
                        tk.Label(detail_content_frame, text=message_content, 
                                justify=tk.LEFT, wraplength=800, 
                                bg=detail_content_frame.cget("background")).pack(fill="x")
        
        # Treeview에서 선택 이벤트 발생 시 상세 내용을 표시하도록 연결
        tree.bind("<<TreeviewSelect>>", show_selected_message)
    
    # 좌측 프레임에 '전체 SMS 목록 보기' 버튼을 추가하여, 버튼 클릭 시 전체 목록을 표시하도록 설정
    all_sms_button = ttk.Button(contact_frame, text="전체 SMS 목록 보기", command=show_all_sms)
    all_sms_button.pack(fill="x", pady=10)
