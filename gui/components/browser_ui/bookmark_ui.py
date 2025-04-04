import tkinter as tk
from tkinter import ttk, messagebox

from artifact_analyzer.browser.safari.bookmark import get_safari_bookmarks as get_bookmarks


def create_bookmark_ui(parent):
    """
    브라우저 북마크 UI 생성
    
    Args:
        parent: 상위 프레임
        
    Returns:
        bookmark_tree: 북마크 트리뷰 위젯
    """
    bookmark_card = ttk.Frame(parent, padding=15)
    bookmark_card.pack(fill="both", expand=True, padx=5, pady=5)
    
    bookmark_tree = ttk.Treeview(bookmark_card, columns=("folder", "title", "url"), show="headings")
    bookmark_tree.heading("folder", text="폴더", anchor="w")
    bookmark_tree.heading("title", text="제목", anchor="w")
    bookmark_tree.heading("url", text="URL", anchor="w")
    bookmark_tree.column("folder", width=200, anchor="w")
    bookmark_tree.column("title", width=180, anchor="w")
    bookmark_tree.column("url", width=320, anchor="w")
    
    # 스크롤바 추가
    vsb = ttk.Scrollbar(bookmark_card, orient="vertical", command=bookmark_tree.yview)
    bookmark_tree.configure(yscrollcommand=vsb.set)
    
    bookmark_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    vsb.pack(side="right", fill="y", pady=5)
    
    return bookmark_tree

def fetch_bookmarks(browser_name, bookmark_tree, backup_path):
    """
    선택한 브라우저의 북마크 데이터 가져오기
    
    Args:
        browser_name: 브라우저 이름
        bookmark_tree: 북마크 트리뷰 위젯
        backup_path: 백업 파일 경로
    """
    # 트리뷰 초기화
    bookmark_tree.delete(*bookmark_tree.get_children())
    
    try:
        if browser_name == "Safari":
            bookmarks = get_bookmarks(backup_path)
        elif browser_name == "Chrome":
            bookmarks = get_chrome_bookmarks(backup_path)
        elif browser_name == "Firefox":
            bookmarks = get_firefox_bookmarks(backup_path)
        elif browser_name == "Edge":
            bookmarks = get_edge_bookmarks(backup_path)
        else:
            bookmarks = f"{browser_name} 북마크 로드 기능이 아직 구현되지 않았습니다."
        
        if isinstance(bookmarks, str):
            bookmark_tree.insert("", "end", values=(browser_name, bookmarks, ""))
        elif bookmarks:
            for bookmark in bookmarks:
                if len(bookmark) == 2:
                    title, url = bookmark
                    folder = "기본 폴더"
                else:
                    folder, title, url = bookmark
                
                bookmark_tree.insert("", "end", values=(folder, title, url))
        else:
            bookmark_tree.insert("", "end", values=(browser_name, "북마크를 찾을 수 없습니다.", ""))
    
    except Exception as e:
        messagebox.showerror("오류", f"{browser_name} 북마크 로드 중 오류 발생: {str(e)}")
        bookmark_tree.insert("", "end", values=(browser_name, f"오류: {str(e)}", ""))