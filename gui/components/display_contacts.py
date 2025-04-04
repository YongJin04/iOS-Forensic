import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import io
import re
from tkinter import font
from artifact_analyzer.call.contact_analyzer import ContactAnalyzer

def display_contacts(parent_frame, backup_path):
    """
    연락처 분석 화면을 표시하는 함수
    
    Args:
        parent_frame: 부모 프레임
        backup_path: iOS 백업 경로
    """
    # 기존 위젯 제거
    for widget in parent_frame.winfo_children():
        widget.destroy()
        
    # 메인 프레임 생성
    main_frame = ttk.Frame(parent_frame)
    main_frame.pack(fill="both", expand=True)
    
    # 헤더 영역
    header_frame = ttk.Frame(main_frame)
    header_frame.pack(fill="x", pady=10)
    
    ttk.Label(header_frame, text="연락처 분석", style="Header.TLabel").pack(side="left")
    
    # 검색창
    search_frame = ttk.Frame(header_frame)
    search_frame.pack(side="right")
    
    ttk.Label(search_frame, text="검색:").pack(side="left")
    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
    search_entry.pack(side="left", padx=5)
    
    # 로딩 메시지
    loading_label = ttk.Label(main_frame, text="연락처 정보 로드 중...", style="Info.TLabel")
    loading_label.pack(pady=20)
    
    # 분석기 클래스 초기화
    analyzer = ContactAnalyzer(backup_path)
    
    # 콘텐츠 프레임
    content_frame = ttk.Frame(main_frame)
    
    # 연락처 목록과 상세 정보를 나누는 패널
    paned_window = ttk.PanedWindow(content_frame, orient="horizontal")
    paned_window.pack(fill="both", expand=True, pady=10)
    
    # 연락처 목록 프레임
    contacts_list_frame = ttk.Frame(paned_window)
    paned_window.add(contacts_list_frame, weight=40)
    
    # 연락처 상세 정보 프레임
    contact_detail_frame = ttk.Frame(paned_window)
    paned_window.add(contact_detail_frame, weight=60)
    
    # 트리뷰(테이블) 생성
    columns = ("name", "phone", "organization")
    tree = ttk.Treeview(contacts_list_frame, columns=columns, show="headings")
    
    tree.heading("name", text="이름")
    tree.heading("phone", text="전화번호")
    tree.heading("organization", text="소속")
    
    tree.column("name", width=120)
    tree.column("phone", width=150)
    tree.column("organization", width=150)
    
    # 스크롤바 추가
    scrollbar = ttk.Scrollbar(contacts_list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    
    # 상세 정보 표시 영역
    detail_view = ttk.Frame(contact_detail_frame)
    detail_view.pack(fill="both", expand=True, padx=10)
    
    # 이미지 표시 라벨
    image_label = ttk.Label(detail_view)
    image_label.pack(pady=10)
    
    # 정보 표시 텍스트 위젯
    detail_text = tk.Text(detail_view, wrap="word", height=15, width=40)
    detail_text.pack(fill="both", expand=True)
    detail_text.config(state="disabled")
    
    # HTML 텍스트 처리 함수
    def display_html_text(text_widget, html_text):
        text_widget.config(state="normal")
        text_widget.delete(1.0, tk.END)
        
        # 볼드체 폰트 설정
        bold_font = font.Font(text_widget, text_widget.cget("font"))
        bold_font.configure(weight="bold")
        text_widget.tag_configure("bold", font=bold_font)
        
        # HTML 태그 처리
        parts = re.split(r'(<b>|</b>|<br>)', html_text)
        bold_mode = False
        
        for part in parts:
            if part == "<b>":
                bold_mode = True
            elif part == "</b>":
                bold_mode = False
            elif part == "<br>":
                text_widget.insert(tk.END, "\n")
            else:
                if bold_mode:
                    text_widget.insert(tk.END, part, "bold")
                else:
                    text_widget.insert(tk.END, part)
        
        text_widget.config(state="disabled")
    
    # 트리뷰 항목 선택 시 상세 정보 표시 함수
    def show_contact_detail(event):
        # 현재 선택한 항목
        selected_item = tree.selection()
        if not selected_item:
            detail_text.config(state="normal")
            detail_text.delete(1.0, tk.END)
            detail_text.config(state="disabled")
            return
            
        # 선택한 항목의 인덱스 가져오기
        item_id = tree.item(selected_item[0], "values")[3]  # 인덱스 값 (hidden)
        
        # 해당 연락처 찾기
        contact = None
        for c in filtered_contacts:
            if str(c.rowid) == item_id:
                contact = c
                break
                
        if contact:
            # 상세 정보 표시 (HTML 처리 함수 사용)
            display_html_text(detail_text, contact.get_formatted_details())
            
            # 이미지 표시
            if contact.image:
                try:
                    image = Image.open(io.BytesIO(contact.image))
                    image = image.resize((150, 150), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    image_label.config(image=photo)
                    image_label.image = photo  # 참조 유지
                except Exception:
                    image_label.config(image="")
            else:
                image_label.config(image="")
    
    # 트리뷰 이벤트 연결
    tree.bind("<<TreeviewSelect>>", show_contact_detail)
    
    # 검색 기능
    def on_search(*args):
        populate_treeview(search_var.get())
    
    search_var.trace("w", on_search)
    
    # 트리뷰에 데이터 채우기
    def populate_treeview(search_query=""):
        # 이전 항목 지우기
        tree.delete(*tree.get_children())
        
        nonlocal filtered_contacts
        filtered_contacts = analyzer.search_contacts(search_query)
        
        for i, contact in enumerate(filtered_contacts):
            full_name = f"{contact.last_name} {contact.first_name}".strip()
            phone = contact.get_phone_number()
            org = contact.organization
            
            # 마지막 값은 rowid (보이지 않는 식별자)
            tree.insert("", "end", values=(full_name, phone, org, contact.rowid))
    
    # 연락처 데이터 로드
    def load_data():
        success, message = analyzer.load_contacts()
        loading_label.destroy()
        
        if success:
            content_frame.pack(fill="both", expand=True)
            populate_treeview()
        else:
            messagebox.showerror("오류", message)
            ttk.Label(main_frame, text="연락처 정보를 불러올 수 없습니다.", style="Error.TLabel").pack(pady=20)
    
    # 필터링된 연락처를 저장할 변수
    filtered_contacts = []
    
    # 데이터 로드 시작
    main_frame.after(100, load_data)