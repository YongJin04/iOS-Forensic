# gui_events.py

import tkinter as tk
from tkinter import filedialog, messagebox
import os

from backup_analyzer.manifest_utils import load_manifest_plist
from gui.file_list_utils import build_file_list_tree

def browse_backup_path(path_var, password_entry, password_var, enable_pw_var):
    """ 폴더 선택 후 암호화 여부 확인 """
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        path_var.set(folder_selected)
        check_encryption_status(folder_selected, password_entry, password_var, enable_pw_var)

def check_encryption_status(backup_path, password_entry, password_var, enable_pw_var):
    """ 백업이 암호화되었는지 확인하고 Password 입력 활성화 여부 설정 """
    manifest_data = load_manifest_plist(backup_path)
    is_encrypted = manifest_data.get("IsEncrypted", False)

    if is_encrypted:
        enable_pw_var.set(1)  # 자동으로 체크 활성화
        password_entry.config(state="normal")
    else:
        enable_pw_var.set(0)  # 자동으로 체크 해제
        password_entry.config(state="disabled")
        password_var.set("")

def toggle_password_entry(enable_pw_var, password_entry, password_var):
    """ Enable Password 체크박스 상태에 따라 Password 입력 활성화 """
    if enable_pw_var.get():
        password_entry.config(state="normal")
    else:
        password_entry.config(state="disabled")
        password_var.set("")

def on_backup_tree_select(event, file_list_tree, tree_widget):
    """
    Backup Tree에서 디렉토리를 선택했을 때 File List 트리를 갱신
    (선택된 노드의 values[0] = 풀패스)
    """
    selected_item = tree_widget.selection()
    if not selected_item:
        return

    values = tree_widget.item(selected_item[0], "values")
    if not values:
        # 예: 루트 노드("System Files") 등에는 values가 없을 수 있음
        return

    full_path = values[0]  # 예: "CameraRollDomain/Media/DCIM"

    # File List Tree 갱신: 기존 노드들 삭제 후, 선택된 디렉토리의 서브트리를 추가
    file_list_tree.delete(*file_list_tree.get_children())

    sub_dict = tree_widget.path_dict.get(full_path, {})
    build_file_list_tree(file_list_tree, sub_dict, parent="", full_path=full_path)

def on_file_list_tree_open(event, file_list_tree, tree_widget):
    """
    File List Tree에서 디렉토리를 열 때(토글 펼침),
    Backup Tree에서도 해당 디렉토리를 열어주기
    """
    selected_item = file_list_tree.focus()  # 현재 열리는 노드
    if not selected_item:
        return

    values = file_list_tree.item(selected_item, "values")
    if not values:
        return

    full_path = values[0]

    # Backup Tree에서도 해당 노드를 찾아 열어줌
    node_id = tree_widget.backup_tree_nodes.get(full_path)
    if node_id:
        tree_widget.item(node_id, open=True)
        tree_widget.see(node_id)

def on_file_list_double_click(event, file_list_tree, tree_widget):
    """
    File List에서 디렉토리를 더블클릭하면,
    Backup Tree에서도 해당 디렉토리를 선택/열기
    (파일이면 동작 안 함)
    """
    selected_item = file_list_tree.selection()
    if not selected_item:
        return

    values = file_list_tree.item(selected_item[0], "values")
    if not values:
        return

    full_path = values[0]
    # 디렉토리인지 확인
    subtree = tree_widget.path_dict.get(full_path)
    if not subtree:
        # 디렉토리가 아니라 파일이거나 없는 경로
        return

    # Backup Tree에서 해당 디렉토리 노드를 선택/열기
    node_id = tree_widget.backup_tree_nodes.get(full_path)
    if node_id:
        tree_widget.selection_set(node_id)
        tree_widget.focus(node_id)
        tree_widget.item(node_id, open=True)
        tree_widget.see(node_id)
