# gui/styles.py
import tkinter as tk
from tkinter import ttk

def apply_styles(root):
    # 테마 색상 정의
    colors = {
        'primary': '#5794FF',         # 선택
        'primary_light': '#88B6FF',   # 기본
        'primary_dark': '#0039cb',    
        'accent': '#00b0ff',          
        'success': '#00c853',         
        'warning': '#ffd600',         
        'error': '#ff3d00',           
        'bg_light': '#ffffff',        
        'bg_medium': '#f5f7fa',       
        'bg_dark': '#e1e5eb',         
        'text_primary': '#24292e',    
        'text_secondary': '#6a737d',  
        'border': '#dfe2e5'           
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
    define_notebook_styles(style, colors)
    define_tab_styles(style, colors)  # 새 탭 배경 스타일 추가
    
    return colors

def define_base_styles(style, colors):
    # 모든 TFrame의 기본 배경을 그대로 사용하지만, 필요시 하위 스타일에서 덮어씀
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
    
    style.configure("Accent.TButton", 
                   background=colors['primary_light'],
                   foreground='white',
                   padding=6,
                   font=("Arial", 10, "bold"))
    style.map("Accent.TButton",
             background=[("active", colors['primary']), 
                         ("pressed", colors['primary_dark'])],
             foreground=[("active", "white"), 
                         ("pressed", "white")])

def define_input_styles(style, colors):
    style.configure("TCheckbutton", 
                   background=colors['bg_light'], 
                   foreground=colors['text_primary'],
                   focusthickness=0,
                   font=("Arial", 10))
    
    style.configure("TEntry", 
                   background=colors['bg_light'],
                   foreground=colors['text_primary'],
                   fieldbackground='white',
                   insertcolor=colors['text_primary'],
                   borderwidth=1,
                   padding=8,
                   relief="solid")
    style.map("TEntry",
             bordercolor=[("focus", colors['primary'])],
             foreground=[("disabled", "#999999")],
             fieldbackground=[("disabled", "#eeeeee")])
    
    style.configure("TCombobox", 
                   background=colors['bg_light'],
                   foreground=colors['text_primary'],
                   fieldbackground='white',
                   padding=5)
    style.map("TCombobox",
             fieldbackground=[("readonly", colors['bg_light'])],
             background=[("readonly", colors['bg_medium'])])

def define_list_styles(style, colors):
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
    
    style.configure("Treeview.Heading", 
                   background=colors['bg_medium'],
                   foreground=colors['text_primary'],
                   relief="flat",
                   font=("Arial", 10, "bold"))
    style.map("Treeview.Heading",
             background=[("active", colors['bg_dark'])])
    
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
    # 카드 프레임 (모든 박스의 테두리 및 배경 색상 변경)
    style.configure("Card.TFrame", 
                   background=colors['bg_light'],  # "#768fff"
                   relief="ridge",
                   borderwidth=1)
    
    # 툴바 프레임
    style.configure("Toolbar.TFrame", 
                   background=colors['bg_medium'],
                   relief="flat")
    
    style.configure("TSeparator", 
                   background=colors['border'])

def define_notebook_styles(style, colors):
    # Notebook 및 탭의 배경을 변경 (테마에 따라 반영되지 않을 수 있음)
    style.configure("TNotebook", background=colors['bg_light'])
    style.configure("TNotebook.Tab", background=colors['bg_light'], foreground=colors['text_primary'])
    style.map("TNotebook.Tab", background=[("selected", colors['primary_light']), 
                                             ("active", colors['primary'])])

def define_tab_styles(style, colors):
    # Evidence, Artifact Analysis 등 탭 내에 사용하는 프레임 스타일 (배경을 "#768fff"로)
    style.configure("Tab.TFrame", background=colors['bg_light'])
