import os
from tkinter import messagebox

from backup_analyzer.manifest_utils import load_manifest_plist, load_manifest_db
from backup_analyzer.build_tree import *
from backup_analyzer.backup_decrypt_utils import is_backup_encrypted


# ──────────────────────────────────────────────────────────────────────────────
def load_backup(
    backup_path: str,
    password: str,
    tree_widget,
    enable_pw_var,
    enable_pw_check,
    password_entry,
    file_list_tree,
    status_label=None,
    icon_dict=None,
    flag_container=None,
) -> None:
    """Load the backup and update UI components accordingly."""
    def update_status(message: str) -> None:
        if status_label:
            status_label.config(text=message)
            status_label.update()

    update_status("Checking backup directory...")
    if not check_backup_directory(backup_path):
        update_status("Error: Invalid backup directory")
        return

    update_status("Loading Manifest.plist file...")
    manifest_data = load_manifest_plist(backup_path)
    if not manifest_data:
        update_status("Error: Manifest.plist file not found")
        messagebox.showwarning("Warning", "Manifest.plist file could not be found.")
        return

    encrypted = is_backup_encrypted(backup_path)

    if encrypted:
        update_status("Error: Encrypted backup – decryption not supported")
        messagebox.showerror(
            "Error",
            "This backup is encrypted.\n"
            "Please create a decrypted backup using iTunes or Finder and try again.",
        )
        return

    update_status("Loading Manifest.db file...")
    file_info_list = load_manifest_db(backup_path)
    if not file_info_list:
        update_status("Error: Manifest.db file not found")
        messagebox.showwarning("Warning", "Manifest.db file could not be found.")
        return

    update_status("Building file tree...")
    file_tree, _ = build_tree(file_info_list)

    update_status("Building backup tree...")
    if icon_dict:
        path_dict, backup_tree_nodes = build_backup_tree(
            tree_widget, file_tree, icon_dict
        )
    else:
        path_dict, backup_tree_nodes = build_backup_tree(tree_widget, file_tree)

    tree_widget.path_dict = path_dict
    tree_widget.backup_tree_nodes = backup_tree_nodes

    file_list_tree.delete(*file_list_tree.get_children())

    update_status("Backup loaded successfully")
    messagebox.showinfo("Complete", "Backup has been successfully loaded!")

    if flag_container is not None:
        flag_container["loaded"] = True


def check_backup_directory(backup_path: str) -> bool:
    """Validate the backup directory path."""
    if not backup_path:
        messagebox.showerror("Error", "Please enter the backup directory.")
        return False
    if not os.path.isdir(backup_path):
        messagebox.showerror("Error", f"Invalid directory: {backup_path}")
        return False
    return True
