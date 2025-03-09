# file_list_utils.py

import tkinter as tk
from tkinter import ttk

def build_file_list_tree(file_list_tree, sub_dict, parent="", full_path=""):
    """
    File List Tree를 구성하는 함수.
    sub_dict: { '폴더명': { ... }, '파일명': file_meta } 형태
    parent: 상위 Treeview 노드 ID
    full_path: 상위까지의 풀패스 (슬래시 구분)

    - 이름이 없는 항목(빈 문자열)은 표시하지 않는다.
    """
    for name, child_obj in sorted(sub_dict.items()):
        # 이름이 없는 경우(빈 문자열) 건너뛰기
        if not name:
            continue

        new_path = (full_path + "/" + name).strip("/")
        if isinstance(child_obj, dict):
            # 디렉토리
            node_id = file_list_tree.insert(
                parent, "end", text=name, values=(new_path,)
            )
            # 하위 디렉토리/파일 재귀
            build_file_list_tree(file_list_tree, child_obj, node_id, new_path)
        else:
            # 파일
            file_list_tree.insert(
                parent, "end", text=name, values=(new_path,)
            )
