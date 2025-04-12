import tkinter as tk
from tkinter import ttk

def create_backup_tree_frame(parent,colors):
    """백업 트리 프레임을 생성합니다."""
    frame = ttk.Frame(parent, padding=5)

    # 트리뷰와 스크롤바를 위한 프레임
    tree_frame = ttk.Frame(frame)
    tree_frame.pack(fill="both", expand=True)

    # 트리뷰 스크롤바
    tree_scrollbar = ttk.Scrollbar(tree_frame)
    tree_scrollbar.pack(side="right", fill="y")

    # 백업 구조 트리뷰
    backup_tree = ttk.Treeview(
        tree_frame, selectmode="browse", yscrollcommand=tree_scrollbar.set
    )
    backup_tree.pack(side="left", fill="both", expand=True)

    # 트리뷰 헤더 설정
    backup_tree.heading("#0", text="Directory Tree", anchor="w")

    folder_icon = tk.PhotoImage(file="gui/icon/folder.png").subsample(30, 30) 
    file_icon = tk.PhotoImage(file="gui/icon/file.png").subsample(30,30)  
    image_icon = tk.PhotoImage(file="gui/icon/picture.png").subsample(30, 30)   


    icon_dict = {
        "folder": folder_icon,
        "file": file_icon,
        "image": image_icon,

    }

    def get_file_icon(filename):
        """파일 확장자에 따라 적절한 아이콘을 반환"""
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            return "image"
        else:
            return "file"

    # 트리뷰에 항목을 추가하는 함수
    def add_tree_item(parent, name, size="", date="", item_type="file"):
        icon_key = "folder" if item_type == "folder" else get_file_icon(name)
        return backup_tree.insert(parent, "end", text=name, values=(size, date, item_type), image=icon_dict[icon_key])

    # 스크롤바 연결
    tree_scrollbar.config(command=backup_tree.yview)

    return {
        'backup_tree_frame': frame,
        'backup_tree': backup_tree,
        'add_tree_item': add_tree_item,
        'icon_dict': icon_dict  
    }
