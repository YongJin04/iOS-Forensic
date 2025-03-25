# gui/styles.py
import tkinter as tk
from tkinter import ttk

def apply_styles(root):
    # 테마 색상 정의
    colors = {
        'primary': '#2962ff',         # 파란색 계열 주요 색상
        'primary_light': '#768fff',   # 밝은 파란색
        'primary_dark': '#0039cb',    # 진한 파란색
        'accent': '#00b0ff',          # 액센트 색상 (하이라이트)
        'success': '#00c853',         # 성공 상태 색상
        'warning': '#ffd600',         # 경고 상태 색상
        'error': '#ff3d00',           # 오류 상태 색상
        'bg_light': '#ffffff',        # 밝은 배경
        'bg_medium': '#f5f7fa',       # 중간 톤 배경
        'bg_dark': '#e1e5eb',         # 어두운 배경
        'text_primary': '#24292e',    # 주요 텍스트 색상
        'text_secondary': '#6a737d',  # 부가 텍스트 색상
        'border': '#dfe2e5'           # 테두리 색상
    }
    
    # 스타일 설정
    style = ttk.Style(root)
    available_themes = style.theme_names()
    
    if 'clam' in available_themes:
        style.theme_use('clam')
    
    # 기본 스타일 정의
    define_base_styles(style, colors)
    define_button_styles(style, colors)
    define_input_styles(style, colors)
    define_list_styles(style, colors)
    define_panel_styles(style, colors)
    
    return colors

def define_base_styles(style, colors):
    # 프레임
    style.configure("TFrame", background=colors['bg_light'])
    
    # 레이블
    style.configure("TLabel", 
                   background=colors['bg_light'], 
                   foreground=colors['text_primary'], 
                   font=("Arial", 10))
    
    # 헤더 레이블
    style.configure("Header.TLabel", 
                   background=colors['bg_light'], 
                   foreground=colors['primary'], 
                   font=("Arial", 16, "bold"))
    
    # 서브헤더 레이블
    style.configure("Subheader.TLabel", 
                   background=colors['bg_light'], 
                   foreground=colors['text_primary'], 
                   font=("Arial", 12, "bold"))

def define_button_styles(style, colors):
    # 버튼 - 기본
    style.configure("TButton", 
                   background=colors['bg_medium'],
                   foreground=colors['text_primary'],
                   borderwidth=0,
                   focusthickness=0,
                   focuscolor=colors['primary'],
                   relief="flat",
                   padding=6,
                   font=("Arial", 10))
    style.map("TButton",
             background=[("active", colors['bg_dark']), 
                         ("pressed", colors['bg_dark'])],
             relief=[("pressed", "flat")])
    
    # 버튼 - 강조(액센트) 스타일
    style.configure("Accent.TButton", 
                   background=colors['primary'],
                   foreground='white',
                   padding=6,
                   font=("Arial", 10, "bold"))
    style.map("Accent.TButton",
             background=[("active", colors['primary_light']), 
                         ("pressed", colors['primary_dark'])],
             foreground=[("active", "white"), 
                         ("pressed", "white")])

def define_input_styles(style, colors):
    # 체크버튼
    style.configure("TCheckbutton", 
                   background=colors['bg_light'], 
                   foreground=colors['text_primary'],
                   focusthickness=0,
                   font=("Arial", 10))
    
    # 입력 필드
    style.configure("TEntry", 
                   background=colors['bg_light'],
                   foreground=colors['text_primary'],
                   fieldbackground='white',
                   insertcolor=colors['text_primary'],
                   borderwidth=1,
                   padding=8,
                   relief="solid")
    style.map("TEntry",
             bordercolor=[("focus", colors['primary'])])
    
    # 콤보박스
    style.configure("TCombobox", 
                   background=colors['bg_light'],
                   foreground=colors['text_primary'],
                   fieldbackground='white',
                   padding=5)
    style.map("TCombobox",
             fieldbackground=[("readonly", colors['bg_light'])],
             background=[("readonly", colors['bg_medium'])])

def define_list_styles(style, colors):
    # 트리뷰
    style.configure("Treeview", 
                   background=colors['bg_light'],
                   foreground=colors['text_primary'],
                   fieldbackground=colors['bg_light'],
                   borderwidth=0,
                   font=("Arial", 10),
                   rowheight=26)
    style.map("Treeview",
             background=[("selected", colors['primary_light'])],
             foreground=[("selected", colors['bg_light'])])
    
    # 트리뷰 헤더
    style.configure("Treeview.Heading", 
                   background=colors['bg_medium'],
                   foreground=colors['text_primary'],
                   relief="flat",
                   font=("Arial", 10, "bold"))
    style.map("Treeview.Heading",
             background=[("active", colors['bg_dark'])])
    
    # 스크롤바
    style.configure("TScrollbar", 
                   background=colors['bg_medium'],
                   borderwidth=0,
                   arrowsize=12,
                   relief="flat",
                   troughcolor=colors['bg_light'])
    style.map("TScrollbar",
             background=[("active", colors['bg_dark']), 
                        ("pressed", colors['primary_light'])])

def define_panel_styles(style, colors):
    # 패널 프레임 (카드 모양)
    style.configure("Card.TFrame", 
                   background=colors['bg_light'],
                   relief="ridge",
                   borderwidth=1)
    
    # 툴바 프레임
    style.configure("Toolbar.TFrame", 
                   background=colors['bg_medium'],
                   relief="flat")
    
    # 구분선
    style.configure("TSeparator", 
                   background=colors['border'])