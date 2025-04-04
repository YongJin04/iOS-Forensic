import tkinter as tk
from tkinter import ttk

from gui.components.browser_ui.history_ui import create_history_ui, fetch_history
from gui.components.browser_ui.bookmark_ui import create_bookmark_ui, fetch_bookmarks
from gui.components.browser_ui.thumbnail_ui import create_thumbnail_ui, fetch_thumbnails

def display_browser(content_frame, backup_path):
    """
    브라우저 관련 UI를 표시하는 메인 함수
    
    Args:
        content_frame: UI를 표시할 프레임
        backup_path: 백업 파일 경로
    """
    # 기존 위젯 삭제
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    # 헤더 추가
    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill="x", pady=(0, 10))
    
    ttk.Label(header_frame, text="🌐 브라우저", style="ContentHeader.TLabel").pack(side="left")
    
    # 브라우저 선택 프레임 추가
    browser_select_frame = ttk.Frame(content_frame)
    browser_select_frame.pack(fill="x", pady=(5, 10))
    
    ttk.Label(browser_select_frame, text="브라우저 선택:").pack(side="left", padx=(0, 5))
    browser_var = tk.StringVar(value="Safari")
    browser_combo = ttk.Combobox(browser_select_frame, textvariable=browser_var, values=["Chrome", "Safari", "Firefox", "Edge"])
    browser_combo.pack(side="left", padx=(0, 10))
    
    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))
    
    # 탭 생성
    notebook = ttk.Notebook(content_frame)
    notebook.pack(fill="both", expand=True)
    
    # 검색기록 탭
    history_frame = ttk.Frame(notebook)
    notebook.add(history_frame, text="검색 기록")
    
    # 북마크 탭
    bookmark_frame = ttk.Frame(notebook)
    notebook.add(bookmark_frame, text="북마크")
    
    # 썸네일 탭 추가
    thumbnail_frame = ttk.Frame(notebook)
    notebook.add(thumbnail_frame, text="썸네일")
    
    # 각 탭에 대한 UI 구성
    history_tree = create_history_ui(history_frame)
    bookmark_tree = create_bookmark_ui(bookmark_frame)
    thumbnail_canvas = create_thumbnail_ui(thumbnail_frame)
    
    # 브라우저 데이터 가져오기 함수
    def fetch_browser_data():
        selected_browser = browser_var.get()
        fetch_history(selected_browser, history_tree, backup_path)
        fetch_bookmarks(selected_browser, bookmark_tree, backup_path)
        fetch_thumbnails(selected_browser, thumbnail_canvas, backup_path)
    
    # 브라우저 선택 변경 시 이벤트
    def on_browser_changed(event):
        fetch_browser_data()
    
    browser_combo.bind("<<ComboboxSelected>>", on_browser_changed)
    
    # 초기 실행
    fetch_browser_data()
    
    # 탭 변경 시 데이터 로딩
    def on_tab_selected(event):
        selected_tab = notebook.tab(notebook.select(), "text")
        selected_browser = browser_var.get()
        
        if selected_tab == "검색 기록":
            fetch_history(selected_browser, history_tree, backup_path)
        elif selected_tab == "북마크":
            fetch_bookmarks(selected_browser, bookmark_tree, backup_path)
        elif selected_tab == "썸네일":
            fetch_thumbnails(selected_browser, thumbnail_canvas, backup_path)
    
    notebook.bind("<<NotebookTabChanged>>", on_tab_selected)