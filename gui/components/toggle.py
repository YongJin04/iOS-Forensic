from tkinter import ttk

def toggle_theme(root, colors, theme_btn):
    # 현재 테마 상태 확인 (버튼 텍스트로 판단)
    current_theme = "light" if theme_btn.cget("text") == "🌙" else "dark"
    
    if current_theme == "light":
        # 🌙 어두운 테마 색상
        new_colors = {
            'bg': '#1e1e1e',       # 배경
            'fg': '#ffffff',       # 기본 텍스트
            'frame_bg': '#2d2d30', # 프레임 배경
            'highlight': '#3f3f46',# 강조색
            'accent': '#007acc',   # 액센트 컬러
            'button_bg': '#3c3c3c',# 버튼 배경
            'button_fg': '#ffffff',# 버튼 글자색
            'entry_bg': '#252526', # 입력 필드 배경
            'entry_fg': '#ffffff', # 입력 필드 글자색
            'border': '#3c3c3c'    # 테두리 색상
        }
        theme_btn.config(text="☀️")  # 햇빛 아이콘으로 변경
    else:
        # ☀️ 밝은 테마 색상
        new_colors = {
            'bg': colors['bg_light'],
            'fg': colors['text_primary'],
            'frame_bg': colors['bg_medium'],
            'highlight': colors['primary_light'],
            'accent': colors['primary'],
            'button_bg': colors['bg_medium'],
            'button_fg': colors['text_primary'],
            'entry_bg': colors['bg_dark'],
            'entry_fg': colors['text_primary'],
            'border': colors['border']
        }
        theme_btn.config(text="🌙")  # 달 아이콘으로 변경
    
    # 전역 colors 딕셔너리 업데이트
    colors.update(new_colors)

    # UI 요소 테마 적용
    root.configure(bg=colors['bg'])

    # 모든 위젯의 색상 업데이트
    update_all_widgets(root, colors)

def update_all_widgets(parent, colors):
    """모든 위젯의 색상을 새 테마에 맞게 업데이트"""
    style = ttk.Style()
    
    for widget in parent.winfo_children():
        widget_type = widget.winfo_class()
        
        if widget_type in ['Frame', 'Labelframe']:
            widget.configure(bg=colors['bg'])
        elif widget_type == 'Label':
            widget.configure(bg=colors['bg'], fg=colors['fg'])
        elif widget_type in ['Button', 'TButton']:
            if isinstance(widget, ttk.Button):
                # ttk 스타일 업데이트
                style.configure("TButton",
                                background=colors['button_bg'],
                                foreground=colors['button_fg'])
                style.map("TButton",
                          background=[("active", colors['highlight']),
                                      ("pressed", colors['frame_bg'])])
            else:
                widget.configure(bg=colors['button_bg'], fg=colors['button_fg'])
        elif widget_type in ['Text', 'Entry']:
            widget.configure(bg=colors['entry_bg'], fg=colors['entry_fg'], 
                             insertbackground=colors['entry_fg'])
        elif widget_type == 'Treeview':
            style.configure("Treeview",
                            background=colors['bg'],
                            fieldbackground=colors['bg'],
                            foreground=colors['fg'],
                            bordercolor=colors['border'])
        
        # 자식 위젯 재귀 처리
        if widget.winfo_children():
            update_all_widgets(widget, colors)
