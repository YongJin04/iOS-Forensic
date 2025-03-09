# load_backup_utils.py

import tkinter as tk
from tkinter import filedialog, messagebox
import os

from backup_analyzer.manifest_utils import load_manifest_plist, load_manifest_db
from backup_analyzer.tree_build_utils import build_file_tree_and_map
from backup_analyzer.decrypt_utils import decrypt_backup

def load_backup(backup_path, password, tree_widget, enable_pw_var, file_list_tree):
    """
    백업을 불러와 Backup Tree 및 File List에 사용할 데이터 구조를 초기화하고,
    TreeView를 갱신한다.

    - Backup Tree에는 '디렉토리'만 표시 (파일은 표시 X)
    - 특히 최하위 디렉토리(하위 디렉토리가 전혀 없는 디렉토리)는 표시하지 않는다.
    - File List Tree는 사용자가 디렉토리를 선택했을 때 build_file_list_tree로 채워짐
    """
    if not backup_path:
        messagebox.showerror("Error", "Backup Directory를 입력해주세요.")
        return
    
    if not os.path.isdir(backup_path):
        messagebox.showerror("Error", f"유효한 디렉토리가 아닙니다: {backup_path}")
        return

    manifest_data = load_manifest_plist(backup_path)
    if not manifest_data:
        messagebox.showwarning("Warning", "Manifest.plist 파일을 찾지 못했습니다.")
        return

    is_encrypted = manifest_data.get("IsEncrypted", False)
    if is_encrypted and not enable_pw_var.get():
        messagebox.showerror("Error", "이 백업은 암호화되어 있습니다. 비밀번호를 입력하세요.")
        return

    # 암호화된 백업인 경우 복호화 시도
    if enable_pw_var.get():
        success = decrypt_backup(backup_path, password)
        if not success:
            messagebox.showerror("Error", "백업 복호화 실패!")
            return

    # Manifest.db 로드
    file_info_list = load_manifest_db(backup_path)
    if not file_info_list:
        messagebox.showwarning("Warning", "Manifest.db 파일을 찾을 수 없습니다.")
        return

    # 전체 트리 구조 구성
    file_tree, _ = build_file_tree_and_map(file_info_list)

    # ---------------------------
    # (1) path_dict를 구축한다.
    #     { "풀패스": { name: (dict or 파일메타), ... }, ... }
    # ---------------------------
    path_dict = {}
    backup_tree_nodes = {}

    # TreeView 초기화 (Backup Tree)
    tree_widget.delete(*tree_widget.get_children())

    # 4개의 루트 노드 (도메인 분류용) 생성
    system_node = tree_widget.insert("", "end", text="System Files")
    user_app_node = tree_widget.insert("", "end", text="User App Files")
    app_group_node = tree_widget.insert("", "end", text="App Group Files")
    app_plugin_node = tree_widget.insert("", "end", text="App Plugin Files")

    def insert_tree(parent, current_dict, current_path=""):
        """
        current_dict: { '폴더명': { ... }, '파일명': file_meta } 형태
        current_path: 상위까지의 풀패스 (슬래시 구분)

        - 디렉토리(child_obj가 dict)만 Backup Tree에 추가하되,
          '하위 디렉토리'가 하나 이상 있는 디렉토리만 추가(=토글이 생기는 디렉토리).
        - 파일은 추가하지 않음.
        - path_dict에는 기존대로 모든 (디렉토리 + 파일) 정보를 저장(파일 리스트 조회용).
        """
        # 현재 디렉토리에 대한 subtree를 path_dict에 등록
        path_dict[current_path] = current_dict

        for name, child_obj in sorted(current_dict.items()):
            # 이름이 없는 디렉토리는 건너뛰기
            if not name:
                continue

            if isinstance(child_obj, dict):
                # 하위 디렉토리가 있는지 확인
                subdirs = {k: v for k, v in child_obj.items() if k and isinstance(v, dict)}
                # subdirs가 비어있지 않으면 -> '토글이 생길 디렉토리'
                if subdirs:
                    new_path = (current_path + "/" + name).strip("/")
                    node_id = tree_widget.insert(parent, "end", text=name, values=(new_path,))
                    backup_tree_nodes[new_path] = node_id
                    # 재귀 호출로 하위 디렉토리도 같은 방식으로 처리
                    insert_tree(node_id, child_obj, new_path)
            else:
                # 파일은 Backup Tree에 추가하지 않음
                continue

    # 도메인별로 분배하여 트리에 추가
    for domain, sub_dict in sorted(file_tree.items()):
        if "AppDomainGroup" in domain:
            insert_tree(app_group_node, {domain: sub_dict}, domain)
        elif "AppDomainPlugin" in domain:
            insert_tree(app_plugin_node, {domain: sub_dict}, domain)
        elif "HomeDomain" in domain or "AppDomain-" in domain:
            insert_tree(user_app_node, {domain: sub_dict}, domain)
        else:
            insert_tree(system_node, {domain: sub_dict}, domain)

    # TreeView(Backup Tree)에 path_dict, backup_tree_nodes 저장
    tree_widget.path_dict = path_dict
    tree_widget.backup_tree_nodes = backup_tree_nodes

    # File List Tree 초기화 (사용자가 디렉토리를 선택해야 표시됨)
    file_list_tree.delete(*file_list_tree.get_children())

    messagebox.showinfo("Complete", "Backup Load Complete!")

if __name__ == "__main__":
    # 테스트 실행 (필요한 경우)
    pass
