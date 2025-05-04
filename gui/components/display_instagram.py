import tkinter as tk
from tkinter import ttk, font
from PIL import Image, ImageTk
import io
import requests
import os
from PIL import ImageDraw

from artifact_analyzer.messenger.instagram.follow import get_instagram_following
from artifact_analyzer.messenger.instagram.account import get_instagram_account_info

class display_instagram:
    def __init__(self, root, backup_path):
        self.root = root
        self.backup_path = backup_path
        self.setup_ui()
        
    def setup_ui(self):
        """GUI 초기 설정"""

         # 기존 위젯 제거
        for widget in self.root.winfo_children():
            widget.destroy()
        self.configure_styles()
        
        # 메인 프레임 설정
        self.main_frame = ttk.Frame(self.root, padding=15)
        self.main_frame.pack(fill="both", expand=True)
        
        self.create_header()
            
        # 탭 컨트롤 생성
        self.tab_control = ttk.Notebook(self.main_frame)
        self.tab_control.pack(fill="both", expand=True, pady=10)
        
        # 계정 정보 탭
        self.account_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.account_tab, text=" 계정 정보 ")
        
        # 팔로잉 목록 탭
        self.following_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.following_tab, text=" 팔로잉 목록 ")
        
        # 각 탭 내용 초기화
        self.setup_account_tab()
        self.setup_following_tab()
        
        # 상태 바
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill="x", side="bottom", pady=(10, 0))
        self.status_label = ttk.Label(self.status_frame, text="준비됨", anchor="e")
        self.status_label.pack(side="right")
        
    def configure_styles(self):
        """스타일 설정"""
        style = ttk.Style()
        
        # 인스타그램 색상 팔레트
        instagram_blue = "#0095F6"
        instagram_dark = "#262626"
        instagram_light = "#FAFAFA"
        instagram_border = "#DBDBDB"
        
        # 폰트 설정
        default_font = font.nametofont("TkDefaultFont").actual()
        header_font = (default_font["family"], 16, "bold")
        subheader_font = (default_font["family"], 12, "bold")
        
        # 프레임 스타일
        style.configure("Card.TFrame", background="white", borderwidth=1, relief="solid")
        style.configure("Header.TFrame", background=instagram_light)
        
        # 레이블 스타일
        style.configure("Header.TLabel", font=header_font, foreground=instagram_dark)
        style.configure("SubHeader.TLabel", font=subheader_font, foreground=instagram_dark)
        style.configure("ContentHeader.TLabel", font=subheader_font, foreground=instagram_dark)
        style.configure("CardTitle.TLabel", font=subheader_font, foreground=instagram_dark)
        style.configure("CardBody.TLabel", foreground=instagram_dark)
        style.configure("CardSectionHeader.TLabel", font=subheader_font, foreground=instagram_dark)
        
        # 버튼 스타일
        style.configure("Instagram.TButton", background=instagram_blue, foreground="white")
        style.map("Instagram.TButton", background=[("active", "#0077E6")])
        
        # 탭 스타일
        style.configure("TNotebook", background=instagram_light)
        style.configure("TNotebook.Tab", padding=[10, 5], font=(default_font["family"], 10))
        style.map("TNotebook.Tab", 
                  background=[("selected", "white"), ("!selected", instagram_light)],
                  foreground=[("selected", instagram_blue), ("!selected", instagram_dark)])
        
        # 트리뷰 스타일
        style.configure("Treeview", 
                      background="white", 
                      foreground=instagram_dark, 
                      rowheight=25,
                      fieldbackground="white")
        style.map("Treeview", background=[("selected", instagram_blue)], foreground=[("selected", "white")])
        
    def create_header(self):
        """상단 헤더 생성"""
        header_frame = ttk.Frame(self.main_frame, style="Header.TFrame")
        header_frame.pack(fill="x", pady=(0, 10))
        

        # 제목
        title_label = ttk.Label(header_frame, text="인스타그램", style="Header.TLabel")
        title_label.pack(side="left")
    
    def setup_account_tab(self):
        """계정 정보 탭 설정"""
        # 가로/세로 스크롤 가능한 프레임 구현
        # 외부 프레임 생성
        outer_frame = ttk.Frame(self.account_tab)
        outer_frame.pack(fill="both", expand=True)
        
        # 수평 스크롤바 생성
        h_scrollbar = ttk.Scrollbar(outer_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # 수직 스크롤바 생성
        v_scrollbar = ttk.Scrollbar(outer_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        
        # 캔버스 생성 및 스크롤바 연결
        account_canvas = tk.Canvas(outer_frame, bg="white",
                                   xscrollcommand=h_scrollbar.set,
                                   yscrollcommand=v_scrollbar.set)
        account_canvas.pack(side="left", fill="both", expand=True)
        
        # 스크롤바와 캔버스 연결
        h_scrollbar.config(command=account_canvas.xview)
        v_scrollbar.config(command=account_canvas.yview)
        
        # 내용이 들어갈 프레임 생성
        scroll_frame = ttk.Frame(account_canvas)
        
        # 캔버스에 내용 프레임 추가
        window_id = account_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        
        # 내용 프레임 크기 변경 시 캔버스 스크롤 영역 업데이트
        def configure_scroll_region(event):
            account_canvas.configure(scrollregion=account_canvas.bbox("all"))
            # 내용 프레임의 너비가 캔버스 너비보다 작으면 캔버스 너비에 맞추기
            canvas_width = event.width
            account_canvas.itemconfig(window_id, width=max(scroll_frame.winfo_reqwidth(), canvas_width))
        
        scroll_frame.bind("<Configure>", configure_scroll_region)
        
        # 캔버스 크기 변경 시 내부 프레임 너비 업데이트
        def canvas_configure(event):
            canvas_width = event.width
            account_canvas.itemconfig(window_id, width=canvas_width)
        
        account_canvas.bind("<Configure>", canvas_configure)
        
        # 마우스 휠 이벤트 바인딩 (세로 스크롤)
        def _on_mousewheel(event):
            account_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 마우스 휠 이벤트 바인딩 (Shift + 마우스 휠 = 가로 스크롤)
        def _on_shift_mousewheel(event):
            account_canvas.xview_scroll(int(-1*(event.delta/120)), "units")
        
        # Windows/Linux에서 마우스 휠 이벤트 바인딩
        account_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        account_canvas.bind_all("<Shift-MouseWheel>", _on_shift_mousewheel)
        
        # Linux에서 사용되는 버튼 4, 5 바인딩 (업/다운 스크롤)
        account_canvas.bind_all("<Button-4>", lambda e: account_canvas.yview_scroll(-1, "units"))
        account_canvas.bind_all("<Button-5>", lambda e: account_canvas.yview_scroll(1, "units"))
        
        # Linux에서 Shift + 버튼 4, 5 바인딩 (좌/우 스크롤)
        account_canvas.bind_all("<Shift-Button-4>", lambda e: account_canvas.xview_scroll(-1, "units"))
        account_canvas.bind_all("<Shift-Button-5>", lambda e: account_canvas.xview_scroll(1, "units"))
        
        # 계정 정보 표시
        self.display_account_info(scroll_frame)
    
    def setup_following_tab(self):
        """팔로잉 목록 탭 설정"""
        # 팔로잉 목록 표시
        self.display_following(self.following_tab)
    
    def display_account_info(self, content_frame):
        # 기존 위젯 삭제
        for widget in content_frame.winfo_children():
            widget.destroy()


        """인스타그램 계정 정보를 표시합니다."""
        # 헤더 추가
        header_frame = ttk.Frame(content_frame)
        header_frame.pack(fill="x", pady=(10, 20))
        
        ttk.Label(header_frame, text="📱 계정 정보", style="ContentHeader.TLabel").pack(side="left")
        ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 20))
        
        # 여기서 백엔드 함수를 호출하여 계정 정보를 가져옵니다
        # 사용자가 구현할 예정인 함수
        try:
            account_data = get_instagram_account_info(self.backup_path)
            
            # 계정 정보가 없을 경우
            if not account_data:
                no_data_frame = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
                no_data_frame.pack(fill="x", padx=5, pady=5)
                
                ttk.Label(
                    no_data_frame, 
                    text="계정 정보를 찾을 수 없습니다.\n\n백업 파일에 해당 정보가 없거나 접근할 수 없습니다.",
                    style="CardBody.TLabel",
                    justify="center"
                ).pack(expand=True, pady=50)
                return
            
            # 프로필 카드
            profile_card = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
            profile_card.pack(fill="x", padx=5, pady=5)
            
            # 프로필 상단 (이미지 + 기본 정보)
            profile_header = ttk.Frame(profile_card)
            profile_header.pack(fill="x", pady=(0, 15))
            
            # 프로필 이미지 영역
            img_frame = ttk.Frame(profile_header, width=150, height=150)
            img_frame.pack(side="left", padx=(0, 20))
            img_frame.pack_propagate(False)  # 크기 고정
            
            # 프로필 이미지 표시
            self.profile_img_label = ttk.Label(img_frame)
            self.profile_img_label.pack(expand=True)
            
            # 프로필 URL이 있으면 이미지 로드
            if 'profile_picture_url' in account_data and account_data['profile_picture_url']:
                try:
                    response = requests.get(account_data['profile_picture_url'])
                    img_data = response.content
                    image = Image.open(io.BytesIO(img_data))
                    image = image.resize((150, 150))
                    photo = ImageTk.PhotoImage(image)
                    
                    self.profile_img_label.config(image=photo)
                    self.profile_img_label.image = photo  # 참조 유지
                except Exception as e:
                    # 기본 이미지 표시
                    self.create_default_profile_image()
            else:
                # 기본 이미지 표시
                self.create_default_profile_image()
            
            # 기본 계정 정보 표시
            info_frame = ttk.Frame(profile_header)
            info_frame.pack(side="left", fill="both", expand=True)
            
            # 사용자명
            username_frame = ttk.Frame(info_frame)
            username_frame.pack(fill="x", pady=(0, 10))
            
            ttk.Label(username_frame, text="Username:", style="CardTitle.TLabel").pack(side="left")
            ttk.Label(username_frame, text=account_data.get('username', '알 수 없음'), style="CardBody.TLabel").pack(side="left", padx=(5, 0))
            
            # 사용자 ID
            user_id_frame = ttk.Frame(info_frame)
            user_id_frame.pack(fill="x", pady=(0, 10))
            
            ttk.Label(user_id_frame, text="User ID:", style="CardTitle.TLabel").pack(side="left")
            ttk.Label(user_id_frame, text=account_data.get('user_id', '알 수 없음'), style="CardBody.TLabel").pack(side="left", padx=(5, 0))
            
            # 마지막 로그인
            login_frame = ttk.Frame(info_frame)
            login_frame.pack(fill="x", pady=(0, 10))
            
            ttk.Label(login_frame, text="마지막 로그인:", style="CardTitle.TLabel").pack(side="left")
            ttk.Label(login_frame, text=account_data.get('last_login', '알 수 없음'), style="CardBody.TLabel").pack(side="left", padx=(5, 0))
            
            ttk.Separator(profile_card, orient="horizontal").pack(fill="x", pady=15)
            
            # 세션 정보 섹션
            ttk.Label(profile_card, text="세션 정보", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
            
            # 세션 정보 표시를 위한 그리드
            session_frame = ttk.Frame(profile_card)
            session_frame.pack(fill="x", pady=(0, 15))
            
            # 앱 버전
            app_version_frame = ttk.Frame(session_frame)
            app_version_frame.pack(fill="x", pady=(0, 5))
            
            ttk.Label(app_version_frame, text="앱 버전:", width=20, style="CardTitle.TLabel").pack(side="left")
            ttk.Label(app_version_frame, text=account_data.get('app_version', '알 수 없음'), style="CardBody.TLabel").pack(side="left")
            
            # OS 버전
            os_version_frame = ttk.Frame(session_frame)
            os_version_frame.pack(fill="x", pady=(0, 5))
            
            ttk.Label(os_version_frame, text="OS 버전:", width=20, style="CardTitle.TLabel").pack(side="left")
            ttk.Label(os_version_frame, text=account_data.get('os_version', '알 수 없음'), style="CardBody.TLabel").pack(side="left")
            
            # 세션 지속 시간
            duration_frame = ttk.Frame(session_frame)
            duration_frame.pack(fill="x", pady=(0, 5))
            
            ttk.Label(duration_frame, text="세션 지속 시간:", width=20, style="CardTitle.TLabel").pack(side="left")
            ttk.Label(duration_frame, text=f"{account_data.get('session_duration', '알 수 없음')}초", style="CardBody.TLabel").pack(side="left")
            
            # 네트워크 타입
            network_frame = ttk.Frame(session_frame)
            network_frame.pack(fill="x", pady=(0, 5))
            
            ttk.Label(network_frame, text="네트워크 타입:", width=20, style="CardTitle.TLabel").pack(side="left")
            ttk.Label(network_frame, text=account_data.get('network_type', '알 수 없음'), style="CardBody.TLabel").pack(side="left")
            
            
            ttk.Separator(profile_card, orient="horizontal").pack(fill="x", pady=15)
            
            # 추가 정보 섹션 (관련 계정 등)
            ttk.Label(profile_card, text="관련 계정 정보", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 5))
            
            # 관련 계정 정보를 표시할 테이블이나 리스트
            if 'related_accounts' in account_data and account_data['related_accounts']:
                # 관련 계정이 있는 경우
                related_accounts_list = ttk.Treeview(profile_card, columns=("id", "status"), show="headings", height=len(account_data['related_accounts']))
                related_accounts_list.heading("id", text="계정 ID")
                related_accounts_list.heading("status", text="상태")

                related_accounts_list.column("id", width=250, stretch=False)
                related_accounts_list.column("status", width=200, stretch=False)

                for account in account_data['related_accounts']:
                    related_accounts_list.insert("", "end", values=(account.get('id', ''), account.get('status', '')))

                related_accounts_list.pack(pady=(0, 5), anchor="w")

            else:
                # 관련 계정이 없는 경우
                ttk.Label(profile_card, text="관련 계정 정보가 없습니다.", style="CardBody.TLabel").pack(anchor="w", pady=(0, 5))
            
            # 계정 설정 정보 - 개선된 여백 적용
            if 'account_settings' in account_data and account_data['account_settings']:
                ttk.Separator(profile_card, orient="horizontal").pack(fill="x", pady=15)
                ttk.Label(profile_card, text="계정 설정", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
                
                settings_frame = ttk.Frame(profile_card)
                settings_frame.pack(fill="x")
                
                # 그리드 레이아웃으로 변경하여 정렬 개선
                settings_grid = ttk.Frame(settings_frame)
                settings_grid.pack(fill="x", pady=(0, 5))
                
                row = 0
                for key, value in account_data['account_settings'].items():
                    # 레이블에 고정 너비 지정하고 여백 추가
                    label = ttk.Label(settings_grid, text=f"{key}:", style="CardTitle.TLabel", width=45, anchor="w")
                    label.grid(row=row, column=0, sticky="w", padx=(0, 15), pady=3)
                    
                    # 값 표시 레이블 - 왼쪽 정렬, 여백 추가
                    value_label = ttk.Label(settings_grid, text=str(value), style="CardBody.TLabel", anchor="w")
                    value_label.grid(row=row, column=1, sticky="w", padx=(5, 0), pady=3)
                    
                    # 그리드 열 설정으로 최소 너비 확보
                    settings_grid.columnconfigure(0, minsize=350)
                    settings_grid.columnconfigure(1, weight=1, minsize=150)
                    
                    row += 1
            
            # 포렌식 분석 정보
            ttk.Separator(profile_card, orient="horizontal").pack(fill="x", pady=15)
            ttk.Label(profile_card, text="포렌식 분석 정보", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
            
            # 포렌식 정보도 그리드 레이아웃으로 개선
            forensic_grid = ttk.Frame(profile_card)
            forensic_grid.pack(fill="x")
            
            # 여기에 추가 포렌식 분석 정보 표시
            if 'forensic_info' in account_data and account_data['forensic_info']:
                row = 0
                for key, value in account_data['forensic_info'].items():
                    # 레이블에 고정 너비 지정하고 여백 추가
                    label = ttk.Label(forensic_grid, text=f"{key}:", style="CardTitle.TLabel", width=45, anchor="w")
                    label.grid(row=row, column=0, sticky="w", padx=(0, 15), pady=3)
                    
                    # 값 표시 레이블 - 왼쪽 정렬, 여백 추가
                    value_label = ttk.Label(forensic_grid, text=str(value), style="CardBody.TLabel", anchor="w")
                    value_label.grid(row=row, column=1, sticky="w", padx=(5, 0), pady=3)
                    
                    # 그리드 열 설정으로 최소 너비 확보
                    forensic_grid.columnconfigure(0, minsize=350)
                    forensic_grid.columnconfigure(1, weight=1, minsize=150)
                    
                    row += 1
            else:
                ttk.Label(forensic_grid, text="추가 포렌식 정보가 없습니다.", style="CardBody.TLabel").pack(anchor="w", pady=(0, 10))
            
        except Exception as e:
            # 오류 발생 시 처리
            error_frame = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
            error_frame.pack(fill="x", padx=5, pady=5)
            
            ttk.Label(
                error_frame, 
                text=f"계정 정보를 불러오는 중 오류가 발생했습니다.\n\n{str(e)}",
                style="CardBody.TLabel",
                justify="center"
            ).pack(expand=True, pady=50)
    
    def create_default_profile_image(self):
        """기본 프로필 이미지 생성"""
        try:
            default_img = Image.new('RGB', (150, 150), color=(240, 240, 240))
            # 원형 이미지 만들기
            mask = Image.new('L', (150, 150), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 150, 150), fill=255)
            default_img.putalpha(mask)
            
            default_photo = ImageTk.PhotoImage(default_img)
            self.profile_img_label.config(image=default_photo)
            self.profile_img_label.image = default_photo
        except Exception as e:
            print(f"기본 이미지 생성 실패: {e}")
    



    def display_following(self, content_frame):
        """인스타그램 팔로잉 목록을 콘텐츠 프레임에 표시합니다."""
        # 기존 위젯 삭제
        for widget in content_frame.winfo_children():
            widget.destroy()
        
        # 헤더 추가
        header_frame = ttk.Frame(content_frame)
        header_frame.pack(fill="x", pady=(10, 20))
        
        ttk.Label(header_frame, text="📷 인스타그램 팔로잉", style="ContentHeader.TLabel").pack(side="left")
        ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))
        
        # 팔로잉 카드
        following_card = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
        following_card.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 백업 데이터에서 팔로잉 정보 가져오기
        try:
            following_data = get_instagram_following(self.backup_path)
            
            if not following_data:
                # 데이터가 없을 경우 메시지 표시
                ttk.Label(
                    following_card, 
                    text="인스타그램 팔로잉 정보를 찾을 수 없습니다.\n\n백업 파일에 해당 정보가 없거나 접근할 수 없습니다.",
                    style="CardBody.TLabel",
                    justify="center"
                ).pack(expand=True, pady=50)
                return
            
            # 데이터가 있을 경우 팔로잉 표시 영역
            following_paned = ttk.PanedWindow(following_card, orient="horizontal")
            following_paned.pack(fill="both", expand=True, pady=(10, 0))
            
            # 왼쪽: 팔로잉 목록
            following_frame = ttk.Frame(following_paned)
            following_paned.add(following_frame, weight=1)
            
            # 팔로잉 수 표시
            ttk.Label(
                following_frame, 
                text=f"팔로잉 목록 (총 {len(following_data)}명)", 
                style="CardSectionHeader.TLabel"
            ).pack(anchor="w", pady=(0, 10))
            
            following_list = ttk.Treeview(following_frame, columns=("username", "full_name", "followed_by"), show="headings", selectmode="browse")
            following_list.heading("username", text="아이디")
            following_list.heading("full_name", text="이름")
            following_list.heading("followed_by", text="팔로우 상태")
            
            following_list.column("username", width=120)
            following_list.column("full_name", width=150)
            following_list.column("followed_by", width=80, anchor="center")
            
            following_scrollbar = ttk.Scrollbar(following_frame, orient="vertical", command=following_list.yview)
            following_list.configure(yscrollcommand=following_scrollbar.set)
            
            following_list.pack(side="left", fill="both", expand=True)
            following_scrollbar.pack(side="right", fill="y")
            
            # 오른쪽: 프로필 상세
            detail_frame = ttk.Frame(following_paned)
            following_paned.add(detail_frame, weight=20)
            
            ttk.Label(detail_frame, text="프로필 상세", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0,5))
            
            # 프로필 이미지 (기본 이미지)
            profile_img_frame = ttk.Frame(detail_frame, width=150, height=150)
            profile_img_frame.pack(pady=5)
            profile_img_frame.pack_propagate(False)  # 크기 고정
            
            profile_img_label = ttk.Label(profile_img_frame)
            profile_img_label.pack(expand=True)
            
            # 기본 이미지 설정
            try:
                default_img = Image.new('RGB', (150, 150), color=(240, 240, 240))
                default_photo = ImageTk.PhotoImage(default_img)
                profile_img_label.config(image=default_photo)
                profile_img_label.image = default_photo
            except Exception as e:
                print(f"기본 이미지 생성 실패: {e}")
            
            # 프로필 상세 정보
            profile_info_frame = ttk.Frame(detail_frame)
            profile_info_frame.pack(fill="both", expand=True, pady=(0, 5))
            
            profile_info_text = tk.Text(profile_info_frame, wrap="word", height=10)
            profile_info_text.pack(fill="both", expand=True)
            profile_info_text.config(state="disabled")
            
            # following_list 채우기
            for user in following_data:
                following_list.insert("", "end", values=(
                    user.get("username", "알 수 없음"), 
                    user.get("full_name", ""), 
                    "맞팔로우" if user.get("followed_by", False) else "단방향"
                ))
        
            # 선택했을 때 동작
            def on_following_select(event):
                selected_item = following_list.selection()
                if not selected_item:
                    return
                
                index = following_list.index(selected_item)
                if index < 0 or index >= len(following_data):
                    return
                    
                user = following_data[index]
                
                # 프로필 이미지 불러오기
                profile_url = user.get("profile_url", "")
                if profile_url:
                    try:
                        response = requests.get(profile_url)
                        img_data = response.content
                        image = Image.open(io.BytesIO(img_data))
                        image = image.resize((150, 150))  # 사이즈 조정
                        photo = ImageTk.PhotoImage(image)
                        
                        profile_img_label.config(image=photo)
                        profile_img_label.image = photo  # 참조 유지 (중요!)
                    except Exception as e:
                        print(f"프로필 이미지 불러오기 실패: {e}")
                        # 이미지 로드 실패 시 기본 이미지 표시
                        try:
                            default_img = Image.new('RGB', (150, 150), color=(240, 240, 240))
                            default_photo = ImageTk.PhotoImage(default_img)
                            profile_img_label.config(image=default_photo)
                            profile_img_label.image = default_photo
                        except Exception:
                            pass
                else:
                    # 프로필 URL이 없는 경우 기본 이미지 표시
                    try:
                        default_img = Image.new('RGB', (150, 150), color=(240, 240, 240))
                        default_photo = ImageTk.PhotoImage(default_img)
                        profile_img_label.config(image=default_photo)
                        profile_img_label.image = default_photo
                    except Exception:
                        pass
                
                # 텍스트 표시
                profile_info_text.config(state="normal")
                profile_info_text.delete("1.0", "end")
                
                # 인스타그램 스타일로 정보 표시
                profile_info_text.tag_configure("title", font=("Arial", 10, "bold"))
                profile_info_text.tag_configure("value", font=("Arial", 10))
                
                profile_info_text.insert("end", "User ID: ", "title")
                profile_info_text.insert("end", f"{user.get('user_id', '알 수 없음')}\n\n", "value")
                
                profile_info_text.insert("end", "Username: ", "title")
                profile_info_text.insert("end", f"{user.get('username', '알 수 없음')}\n\n", "value")
                
                profile_info_text.insert("end", "Full Name: ", "title")
                profile_info_text.insert("end", f"{user.get('full_name', '')}\n\n", "value")
                
                profile_info_text.insert("end", "Followed By: ", "title")
                profile_info_text.insert("end", f"{'맞팔로우' if user.get('followed_by', False) else '단방향'}\n\n", "value")
                
                # 추가 정보가 있다면 표시
                for key, value in user.items():
                    if key not in ['user_id', 'username', 'full_name', 'profile_url', 'followed_by'] and value:
                        profile_info_text.insert("end", f"{key}: ", "title")
                        profile_info_text.insert("end", f"{value}\n\n", "value")
                
                profile_info_text.config(state="disabled")
            
            following_list.bind("<<TreeviewSelect>>", on_following_select)
            
            # 처음 항목 선택
            if following_data:
                first_item = following_list.get_children()[0]
                following_list.selection_set(first_item)
                following_list.event_generate("<<TreeviewSelect>>")
                
        except Exception as e:
            # 오류 발생 시 처리
            ttk.Label(
                following_card, 
                text=f"팔로잉 정보를 불러오는 중 오류가 발생했습니다.\n\n{str(e)}",
                style="CardBody.TLabel",
                justify="center"
            ).pack(expand=True, pady=50)
