import tkinter as tk
from tkinter import ttk


def create_file_list_frame(parent, colors):
    """
    파일‑리스트 + 프리뷰 프레임을 생성한다.
    위 60 % : 파일 목록, 아래 40 % : 미리보기.
    반환 dict 에 preview_frame / preview_label 도 포함된다.
    """
    outer = ttk.Frame(parent, padding=5)

    vpaned = ttk.PanedWindow(outer, orient="vertical")
    vpaned.pack(fill="both", expand=True)

    # ── 1) 파일‑리스트 영역 ───────────────────────────────────────
    list_frame = ttk.Frame(vpaned)
    vpaned.add(list_frame, weight=6)  # 60 %

    columns = ('__fullpath', 'size', 'type', 'mdate', 'cdate', 'permission')
    tree = ttk.Treeview(
        list_frame,
        columns=columns,
        show='tree headings',
        style="FileList.Treeview",
    )
    tree.heading('#0', text='Name')
    tree.column('#0', width=250)

    tree.column('__fullpath', width=0, stretch=False)
    tree.heading('__fullpath', text='')

    for col, txt, w in [
        ('size', 'Size', 80),
        ('type', 'Type', 100),
        ('mdate', 'Date Modified', 140),
        ('cdate', 'Date Created', 140),
        ('permission', 'Permission', 80),
    ]:
        tree.heading(col, text=txt)
        tree.column(col, width=w, anchor='e' if col == 'size' else 'w')

    tree.pack(side="left", fill="both", expand=True)
    vsb = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    vsb.pack(side="right", fill="y")
    tree.configure(yscrollcommand=vsb.set)

    # ── 2) 프리뷰 영역 ───────────────────────────────────────────
    preview_frame = ttk.Frame(vpaned)
    vpaned.add(preview_frame, weight=4)  # 40 %

    preview_label = ttk.Label(
        preview_frame,
        text="(Preview)",
        anchor="center",
        justify="center",
    )
    preview_label.pack(fill="both", expand=True)

    return {
        'file_list_frame': outer,
        'file_list_tree': tree,
        'file_list_scrollbar': vsb,
        'preview_frame': preview_frame,
        'preview_label': preview_label,
    }
