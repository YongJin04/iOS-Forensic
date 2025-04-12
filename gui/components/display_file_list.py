import tkinter as tk
from tkinter import ttk

def create_file_list_frame(parent, colors):
    """파일 리스트 프레임을 생성합니다."""
    frame = ttk.Frame(parent, padding=5)

    table_frame = ttk.Frame(frame)
    table_frame.pack(fill="both", expand=True)

    # 첫 번째 열은 숨겨진 '__fullpath'
    columns = ('__fullpath', 'size', 'type', 'mdate', 'cdate', 'permission')
    file_list_tree = ttk.Treeview(
        table_frame,
        columns=columns,
        show='tree headings',          # 트리 + 헤더
        style="FileList.Treeview",
    )

    # ── #0(Tree) 컬럼 ──────────────────────────────────────────────
    file_list_tree.heading('#0', text='Name')
    file_list_tree.column('#0', width=250)

    # ── 숨김 열: __fullpath ───────────────────────────────────────
    file_list_tree.column('__fullpath', width=0, stretch=False)
    file_list_tree.heading('__fullpath', text='')       # 헤더 비우기

    # ── 나머지 표시 열 ────────────────────────────────────────────
    file_list_tree.heading('size', text='Size')
    file_list_tree.heading('type', text='Type')
    file_list_tree.heading('mdate', text='Date Modified')
    file_list_tree.heading('cdate', text='Date Created')
    file_list_tree.heading('permission', text='Permission')

    file_list_tree.column('size', width=80, anchor='e')
    file_list_tree.column('type', width=100)
    file_list_tree.column('mdate', width=140)
    file_list_tree.column('cdate', width=140)
    file_list_tree.column('permission', width=80)

    file_list_tree.pack(side="left", fill="both", expand=True)

    vbar = ttk.Scrollbar(table_frame, orient="vertical", command=file_list_tree.yview)
    vbar.pack(side="right", fill="y")
    file_list_tree.configure(yscrollcommand=vbar.set)

    return {
        'file_list_frame': frame,
        'file_list_tree': file_list_tree,
        'file_list_scrollbar': vbar,
    }
