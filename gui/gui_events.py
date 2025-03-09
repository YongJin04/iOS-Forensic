import tkinter as tk
from tkinter import filedialog, messagebox
import os

from backup_analyzer.manifest_utils import load_manifest_plist, load_manifest_db
from backup_analyzer.tree_build_utils import build_file_tree_and_map
from backup_analyzer.decrypt_utils import decrypt_backup

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

def load_backup(backup_path, password, tree_widget, enable_pw_var):
    """ 백업을 불러와 트리에 표시하는 함수 """
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

    if enable_pw_var.get():
        success = decrypt_backup(backup_path, password)
        if not success:
            messagebox.showerror("Error", "백업 복호화 실패!")
            return

    file_info_list = load_manifest_db(backup_path)
    if not file_info_list:
        messagebox.showwarning("Warning", "Manifest.db 파일을 찾을 수 없습니다.")
        return

    file_tree, _ = build_file_tree_and_map(file_info_list)
    tree_widget.delete(*tree_widget.get_children())

    def insert_tree(parent, current_dict):
        for k, v in sorted(current_dict.items()):
            node_id = tree_widget.insert(parent, "end", text=k)
            if v:
                insert_tree(node_id, v)

    for domain, sub_dict in sorted(file_tree.items()):
        domain_node = tree_widget.insert("", "end", text=domain)
        insert_tree(domain_node, sub_dict)

    messagebox.showinfo("Complete", "백업 로드 완료!")
