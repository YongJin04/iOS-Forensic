import tkinter as tk
from tkinter import ttk, messagebox

from artifact_analyzer.browser.safari.bookmark import get_safari_bookmarks as get_bookmarks
# (※ get_chrome_bookmarks / get_firefox_bookmarks / get_edge_bookmarks 는 다른 모듈에 있음)


def create_bookmark_ui(parent):
    """브라우저 북마크 Treeview 생성 – 열: Folder, Title, URL"""
    bookmark_card = ttk.Frame(parent, padding=15)
    bookmark_card.pack(fill="both", expand=True, padx=5, pady=5)

    columns = ("folder", "title", "url")
    bookmark_tree = ttk.Treeview(bookmark_card, columns=columns, show="headings")

    bookmark_tree.heading("folder", text="폴더", anchor="w")
    bookmark_tree.heading("title", text="제목", anchor="w")
    bookmark_tree.heading("url", text="URL", anchor="w")

    bookmark_tree.column("folder", width=200, anchor="w")
    bookmark_tree.column("title", width=180, anchor="w")
    bookmark_tree.column("url", width=320, anchor="w")

    bookmark_tree.tag_configure("even", background="#FFFFFF")
    bookmark_tree.tag_configure("odd", background="#f5f5f5")

    vsb = ttk.Scrollbar(bookmark_card, orient="vertical", command=bookmark_tree.yview)
    bookmark_tree.configure(yscrollcommand=vsb.set)

    bookmark_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    vsb.pack(side="right", fill="y", pady=5)

    return bookmark_tree


def fetch_bookmarks(browser_name: str, bookmark_tree: ttk.Treeview, backup_path):
    """선택 브라우저의 북마크 로드"""
    bookmark_tree.delete(*bookmark_tree.get_children())

    def _insert_message(msg):
        bookmark_tree.insert("", "end", values=(browser_name, msg, ""), tags=("even",))

    try:
        if browser_name == "Safari":
            bookmarks = get_bookmarks(backup_path)
        else:
            bookmarks = f"{browser_name} 북마크 로드 기능이 아직 구현되지 않았습니다."

        if isinstance(bookmarks, str):
            _insert_message(bookmarks)
            return

        if not bookmarks:
            _insert_message("북마크를 찾을 수 없습니다.")
            return

        for idx, bm in enumerate(bookmarks):
            if len(bm) == 2:
                title, url = bm
                folder = "기본 폴더"
            else:
                folder, title, url = bm
            tag = "even" if idx % 2 == 0 else "odd"
            bookmark_tree.insert("", "end", values=(folder, title, url), tags=(tag,))

        # Chrome – 클릭 비활성화
        if browser_name == "Chrome":
            bookmark_tree.configure(selectmode="none")
            bookmark_tree.bind("<Button-1>", lambda e: "break")
        else:
            bookmark_tree.configure(selectmode="extended")
            bookmark_tree.unbind("<Button-1>")

    except Exception as e:
        if browser_name != "Chrome":
            messagebox.showerror("오류", f"{browser_name} 북마크 로드 중 오류 발생: {e}")
        _insert_message(f"오류: {e}")