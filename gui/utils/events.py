from tkinter import filedialog

from backup_analyzer.backup_decrypt_utils import is_backup_encrypted
from backup_analyzer.manifest_utils import load_manifest_plist, load_manifest_db
from backup_analyzer.build_file_list_utils import build_file_list_tree


# ─────────────────────────────────────────────────────────────────────────────
# 기본 기능 (Browse, Toggle, 리스트/트리 동기화) ─ 기존과 동일
# ─────────────────────────────────────────────────────────────────────────────
def browse_backup_path(
        path_var,
        password_entry,
        password_var,
        enable_pw_var,
        enable_pw_check=None,   # ← 선택: “Encrypted” 체크박스 위젯
        pw_toggle_btn=None):    # ← 선택: 👁 비밀번호 토글 버튼
    """
    • 사용자가 백업 폴더를 고르면 즉시 Manifest.db 첫 16 byte를 읽어
      SQLite 매직과 비교해 암호화 여부를 판단한다.
    • 암호화되지 않은 백업이면 비밀번호 입력·토글·체크박스
      **모두 비활성화**.
    """
    folder_selected = filedialog.askdirectory(title="Select iOS backup folder")
    if not folder_selected:
        return          # 사용자가 취소

    path_var.set(folder_selected)
    password_var.set("")          # 이전 입력 초기화

    # ← 헤더 비교(53514c69… SQLite magic) 로 암/복호 여부 판정
    encrypted = is_backup_encrypted(folder_selected)

    if encrypted:
        enable_pw_var.set(1)
        password_entry.config(state="normal")
        if enable_pw_check: enable_pw_check.state(["selected"])
        if pw_toggle_btn:   pw_toggle_btn.config(state="normal")
    else:
        enable_pw_var.set(0)
        password_entry.config(state="disabled")
        if enable_pw_check: enable_pw_check.state(["!selected"])
        if pw_toggle_btn:   pw_toggle_btn.config(state="disabled")

        # 체크가 비활성화되면 토글 버튼도 눌러볼 수 없으므로 표시를 초기화
        pw_toggle_btn and pw_toggle_btn.config(text="👁")


def toggle_password_entry(enable_pw_var, password_entry, password_var):
    """Enables or disables the password entry field based on encryption flag."""
    if enable_pw_var.get():
        password_entry.config(state="normal")
    else:
        password_entry.config(state="disabled")
        password_var.set("")


def update_file_list_from_backup_tree_click(event, file_list_tree, tree_widget, backup_path):
    selected_item = tree_widget.selection()
    if not selected_item:
        return

    values = tree_widget.item(selected_item[0], "values")
    if not values:
        return

    full_path = values[0]
    file_list_tree.delete(*file_list_tree.get_children())

    sub_dict = tree_widget.path_dict.get(full_path, {})
    build_file_list_tree(
        file_list_tree,
        sub_dict,
        parent="",
        full_path=full_path,
        backup_path=backup_path,
    )


def update_backup_tree_from_file_list_double_click(event, file_list_tree, tree_widget):
    """Expands/scrolls the backup tree to the double‑clicked file‑list node."""
    selected_item = file_list_tree.selection()
    if not selected_item:
        return

    values = file_list_tree.item(selected_item[0], "values")
    if not values:
        return

    full_path = values[0]
    node_id = tree_widget.backup_tree_nodes.get(full_path)
    if node_id:
        tree_widget.selection_set(node_id)
        tree_widget.focus(node_id)
        tree_widget.item(node_id, open=True)
        tree_widget.see(node_id)

import os
import sqlite3
import shutil
from tkinter import filedialog

def show_file_paths(event, file_list_tree, backup_path_var):
    item_id = file_list_tree.identify_row(event.y)
    if not item_id:
        return

    file_list_tree.selection_set(item_id)

    values = file_list_tree.item(item_id, "values")
    if not values:
        return

    full_path = values[0]
    #print(f"iPhone path : {full_path}")

    try:
        domain, _, relativePath = full_path.split('/', 2)
        fileName = os.path.basename(full_path)
    except ValueError:
        print("[Error] full_path 분리 실패")
        return

    #print(f"domain        : {domain}")
    #print(f"relativePath  : {relativePath}")
    #print(f"backup_path   : {backup_path_var}")

    manifest_db_path = os.path.join(backup_path_var, "Manifest.db")
    if not os.path.exists(manifest_db_path):
        #print(f"[Error] Manifest.db not found at {manifest_db_path}")
        return

    try:
        conn = sqlite3.connect(manifest_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT fileID FROM Files WHERE domain = ? AND relativePath = ?",
            (domain, relativePath),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            print("[Info] Manifest.db에서 일치하는 파일을 찾지 못했습니다.")
            return
        fileID = row[0]
        #print(f"fileID        : {fileID}")
    except Exception as e:
        print(f"[Error] SQLite 처리 중 오류 발생: {e}")
        return

    src_path = os.path.join(backup_path_var, fileID[:2], fileID)
    #print(f"filePath      : {src_path}")
    #print(f"fileName      : {fileName}")

    if not os.path.exists(src_path):
        print("[Error] 백업 파일이 존재하지 않습니다.")
        return

    dst_path = filedialog.asksaveasfilename(
        title="저장 위치 선택",
        initialfile=fileName,
        defaultextension=os.path.splitext(fileName)[1],
        filetypes=[("All Files", "*.*")],
    )
    if not dst_path:
        print("[Info] 저장이 취소되었습니다.")
        return

    try:
        shutil.copy2(src_path, dst_path)
        print(f"[Success] 파일이 저장되었습니다 → {dst_path}")
    except Exception as e:
        print(f"[Error] 파일 저장 실패: {e}")
