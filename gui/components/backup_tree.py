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

    # 트리뷰 컬럼 설정
    #backup_tree["columns"] = ("size", "date", "type")
    #backup_tree.column("#0", width=250, minwidth=180)
    #backup_tree.column("size", width=80, minwidth=50, anchor="e")
    #backup_tree.column("date", width=120, minwidth=80, anchor="center")
    #backup_tree.column("type", width=0, stretch=False)  # 숨겨진 타입 컬럼

    # 트리뷰 헤더 설정
    backup_tree.heading("#0", text="파일/폴더", anchor="w")
    #backup_tree.heading("size", text="크기", anchor="e")
    #backup_tree.heading("date", text="날짜", anchor="center")

    # 이미지 로드
# 이미지 로드 및 크기 조정
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
