import tkinter as tk
from tkinter import ttk
from gui.components.device_info import *
from gui.components.display_browser import *
from gui.components.message import *
from gui.components.call_history import *
from gui.components.photo import *

def create_artifact_analysis_options(parent, backup_path_var, colors):
    """아티팩트 분석 옵션을 생성합니다."""
    main_frame = ttk.Frame(parent)
    main_frame.pack(fill="both", expand=True)
    
    # 왼쪽 사이드바 - 아티팩트 카테고리
    sidebar = ttk.Frame(main_frame, style="Sidebar.TFrame", padding=10)
    sidebar.pack(side="left", fill="y", padx=(0, 10))
    
    # 카테고리 제목
    ttk.Label(sidebar, text="아티팩트 카테고리", style="SidebarHeader.TLabel").pack(anchor="w", pady=(0, 10))
    
    # 오른쪽 콘텐츠 영역 생성 (여기서 미리 생성)
    content_frame = ttk.Frame(main_frame, style="Content.TFrame", padding=10)
    content_frame.pack(side="right", fill="both", expand=True)
    
    # 카테고리 버튼 생성
    categories = [
        {"name": "디바이스 정보", "icon": "📱", "command": lambda: display_device_info(content_frame, backup_path_var.get())},
        {"name": "브라우저", "icon": "🌐", "command": lambda: display_browser(content_frame, backup_path_var.get())},
        {"name": "카카오톡", "icon": "💬", "command": lambda: display_messages(content_frame, backup_path_var.get())},
        {"name": "연락처", "icon": "📞", "command": lambda: display_call_history(content_frame, backup_path_var.get())},
        {"name": "사진 및 미디어", "icon": "🖼️", "command": lambda: display_photos_media(content_frame, backup_path_var.get())},
    ]
    
    category_buttons = []
    selected_category = tk.StringVar()
    
    # 버튼 생성 함수
    def create_category_button(category, index):
        btn_frame = ttk.Frame(sidebar, style="SidebarItem.TFrame", padding=5)
        btn_frame.pack(fill="x", pady=2)
        
        # 선택 표시기
        indicator = ttk.Frame(btn_frame, width=3, style="Indicator.TFrame")
        indicator.pack(side="left", fill="y", padx=(0, 5))
        
        # 아이콘과 이름이 있는 버튼
        btn = ttk.Button(
            btn_frame,
            text=f"{category['icon']} {category['name']}",
            style="Sidebar.TButton",
            command=lambda: activate_category(index, category)
        )
        btn.pack(fill="x", expand=True)
        return {"button": btn, "indicator": indicator, "frame": btn_frame}
    
    # 카테고리 활성화 함수
    def activate_category(index, category):
        selected_category.set(category["name"])
        # 모든 버튼 비활성화 스타일 적용
        for i, btn_data in enumerate(category_buttons):
            if i == index:
                btn_data["frame"].configure(style="SidebarItemActive.TFrame")
                btn_data["indicator"].configure(style="IndicatorActive.TFrame")
            else:
                btn_data["frame"].configure(style="SidebarItem.TFrame")
                btn_data["indicator"].configure(style="Indicator.TFrame")
        
        # 카테고리에 맞는 콘텐츠 표시
        if category["command"]:
            category["command"]()  # 선택한 카테고리의 함수 실행
    
    # 카테고리 버튼 생성
    for i, category in enumerate(categories):
        button_data = create_category_button(category, i)
        category_buttons.append(button_data)
    
    # 시작 페이지 표시
    show_artifact_welcome_page(content_frame)
    
    return {
        "sidebar": sidebar, 
        "content_frame": content_frame,
        "category_buttons": category_buttons,
        "selected_category": selected_category
    }

def show_artifact_welcome_page(content_frame):
    """아티팩트 분석 시작 페이지를 표시합니다."""
    # 기존 위젯 삭제
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    # 환영 메시지 및 안내 표시
    welcome_frame = ttk.Frame(content_frame, style="Card.TFrame", padding=20)
    welcome_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    ttk.Label(welcome_frame, text="iOS 백업 아티팩트 분석", style="CardHeader.TLabel").pack(pady=(0, 20))
    ttk.Label(welcome_frame, text="왼쪽의 아티팩트 카테고리를 선택하여 분석을 시작하세요.", 
              style="CardText.TLabel", wraplength=400).pack(pady=10)
    
    # 아이콘 설명
    icon_frame = ttk.Frame(welcome_frame)
    icon_frame.pack(pady=20)
    
    icons = [
        {"icon": "📱", "text": "디바이스 정보"},
        {"icon": "💬", "text": "카카오톡"},
        {"icon": "👤", "text": "연락처"},
        {"icon": "🖼️", "text": "미디어"}
    ]
    
    for icon_data in icons:
        icon_item = ttk.Frame(icon_frame)
        icon_item.pack(side="left", padx=15)
        ttk.Label(icon_item, text=icon_data["icon"], font=("Arial", 24)).pack(anchor="center")
        ttk.Label(icon_item, text=icon_data["text"], style="CardText.TLabel").pack(anchor="center")
