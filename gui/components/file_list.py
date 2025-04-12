import tkinter as tk
from tkinter import ttk

def create_file_list_frame(parent, colors):
    """파일 리스트 프레임을 생성합니다."""
    frame = ttk.Frame(parent, padding=5)
    
    # 프레임 헤더
    header_frame = ttk.Frame(frame)
    header_frame.pack(fill="x")
    
    # 파일 목록 테이블
    table_frame = ttk.Frame(frame)
    table_frame.pack(fill="both", expand=True)
    
    # 파일 목록을 위한 트리뷰 (향상된 디자인)
    columns = ('name', 'size', 'type', 'mdate', 'cdate', 'permission')
    file_list_tree = ttk.Treeview(table_frame, columns=columns, show='headings', style="FileList.Treeview")
    
    # 컬럼 헤더 설정
    file_list_tree.heading('name', text='Name')
    file_list_tree.heading('size', text='Size')
    file_list_tree.heading('type', text='Type')
    file_list_tree.heading('mdate', text='Data Modified')
    file_list_tree.heading('cdate', text='Create Modified')
    file_list_tree.heading('permission', text='Permission')
    
    # 컬럼 폭 설정
    file_list_tree.column('name', width=250)
    file_list_tree.column('size', width=80, anchor='e')
    file_list_tree.column('type', width=100)
    file_list_tree.column('mdate', width=140)
    file_list_tree.column('cdate', width=140)
    file_list_tree.column('permission', width=80)
    
    file_list_tree.pack(side="left", fill="both", expand=True)
    
    # 수직 스크롤바
    v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=file_list_tree.yview)
    v_scrollbar.pack(side="right", fill="y")
    file_list_tree.configure(yscrollcommand=v_scrollbar.set)
    
    return {
        'file_list_frame': frame,
        'file_list_tree': file_list_tree,
        'file_list_scrollbar': v_scrollbar
    }