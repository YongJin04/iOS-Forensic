from tkinter import messagebox
import os

from backup_analyzer.manifest_utils import load_manifest_plist, load_manifest_db
from backup_analyzer.build_tree_utils import *
from backup_analyzer.backup_decrypt_utils import decrypt_backup

def load_backup(backup_path, password, tree_widget, enable_pw_var, file_list_tree, status_label=None, icon_dict=None):
    """ Loads the backup data and updates the UI components. """
    # 상태 업데이트 함수
    def update_status(message):
        if status_label:
            status_label.config(text=message)
            status_label.update()  # UI 즉시 업데이트
    
    update_status("백업 디렉토리 확인 중...")
    if not check_backup_directory(backup_path):
        update_status("오류: 잘못된 백업 디렉토리")
        return

    # Load Manifest.plist file
    update_status("Manifest.plist 파일 로드 중...")
    manifest_data = load_manifest_plist(backup_path)
    if not manifest_data:
        update_status("오류: Manifest.plist 파일 찾을 수 없음")
        messagebox.showwarning("경고", "Manifest.plist 파일을 찾을 수 없습니다.")
        return

    # Check if the backup is encrypted and requires a password
    if manifest_data.get("IsEncrypted", False) and not enable_pw_var.get():
        update_status("오류: 암호 필요")
        messagebox.showerror("오류", "이 백업은 암호화되어 있습니다. 암호를 입력하세요.")
        return

    # Decrypt the backup if required
    if enable_pw_var.get():
        update_status("백업 복호화 중...")
        if not decrypt_backup(backup_path, password):
            update_status("오류: 백업 복호화 실패")
            messagebox.showerror("오류", "백업 복호화에 실패했습니다!")
            return

    # Load file information from Manifest.db
    update_status("Manifest.db 파일 로드 중...")
    file_info_list = load_manifest_db(backup_path)
    if not file_info_list:
        update_status("오류: Manifest.db 파일 찾을 수 없음")
        messagebox.showwarning("경고", "Manifest.db 파일을 찾을 수 없습니다.")
        return

    # Build file tree and update UI components
    update_status("파일 트리 구성 중...")
    file_tree, _ = build_tree(file_info_list)
    
    update_status("백업 트리 구성 중...")
    # 아이콘 딕셔너리가 제공된 경우 사용
    if icon_dict:
        path_dict, backup_tree_nodes = build_backup_tree(tree_widget, file_tree, icon_dict)
    else:
        path_dict, backup_tree_nodes = build_backup_tree(tree_widget, file_tree)

    tree_widget.path_dict = path_dict
    tree_widget.backup_tree_nodes = backup_tree_nodes

    # 파일 목록 초기화
    file_list_tree.delete(*file_list_tree.get_children())

    update_status("백업 로드 완료")
    messagebox.showinfo("완료", "백업 로드가 완료되었습니다!")

def check_backup_directory(backup_path):
    """ Checks if the backup directory is valid. """
    if not backup_path:
        messagebox.showerror("Error", "Please enter the Backup Directory.")
        return False
    if not os.path.isdir(backup_path):
        messagebox.showerror("Error", f"Invalid directory: {backup_path}")
        return False
    return True