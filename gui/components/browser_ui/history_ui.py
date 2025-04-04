import tkinter as tk
from tkinter import ttk, messagebox

from artifact_analyzer.browser.safari.history import get_safari_history as get_history

def create_history_ui(parent):
    """
    브라우저 검색 기록 UI 생성
    
    Args:
        parent: 상위 프레임
        
    Returns:
        history_tree: 검색 기록 트리뷰 위젯
    """
    browser_card = ttk.Frame(parent, padding=15)
    browser_card.pack(fill="both", expand=True, padx=5, pady=5)
    
    history_tree = ttk.Treeview(browser_card, columns=("title", "url", "visit_time"), show="headings")
    history_tree.heading("title", text="Title", anchor="w")
    history_tree.heading("url", text="URI", anchor="w")
    history_tree.heading("visit_time", text="방문 시간", anchor="w")
    history_tree.column("title", width=180, anchor="w")
    history_tree.column("url", width=320, anchor="w")
    history_tree.column("visit_time", width=150, anchor="w")
    
    # 스크롤바 추가
    vsb = ttk.Scrollbar(browser_card, orient="vertical", command=history_tree.yview)
    history_tree.configure(yscrollcommand=vsb.set)
    
    history_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    vsb.pack(side="right", fill="y", pady=5)
    
    return history_tree

def fetch_history(browser_name, history_tree, backup_path):
    """
    선택한 브라우저의 검색 기록 데이터 가져오기
    
    Args:
        browser_name: 브라우저 이름
        history_tree: 검색 기록 트리뷰 위젯
        backup_path: 백업 파일 경로
    """
    # 트리뷰 초기화
    history_tree.delete(*history_tree.get_children())
    
    try:
        if browser_name == "Safari":
            history = get_history(backup_path)
        elif browser_name == "Chrome":
            history = get_chrome_history(backup_path)
        elif browser_name == "Firefox":
            history = get_firefox_history(backup_path)
        elif browser_name == "Edge":
            history = get_edge_history(backup_path)
        else:
            history = f"{browser_name} 브라우저 기록 로드 기능이 아직 구현되지 않았습니다."
        
        if isinstance(history, str):
            history_tree.insert("", "end", values=("", history, ""))
        elif history:
            for item in history:
                history_tree.insert("", "end", values=item)
        else:
            history_tree.insert("", "end", values=("", f"{browser_name} 검색 기록을 찾을 수 없습니다.", ""))
    
    except Exception as e:
        messagebox.showerror("오류", f"{browser_name} 검색 기록 로드 중 오류 발생: {str(e)}")
        history_tree.insert("", "end", values=("", f"오류: {str(e)}", ""))