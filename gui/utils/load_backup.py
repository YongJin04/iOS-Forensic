from tkinter import messagebox
import os

from backup_analyzer.manifest_utils import load_manifest_plist, load_manifest_db
from backup_analyzer.build_tree import *
from backup_analyzer.backup_decrypt_utils import decrypt_backup

def load_backup(backup_path, password, tree_widget, enable_pw_var, file_list_tree, status_label=None, icon_dict=None, flag_container=None):
    """ Loads the backup data and updates the UI components. """
    # Status update function
    def update_status(message):
        if status_label:
            status_label.config(text=message)
            status_label.update()  # Immediately update UI

    update_status("Checking backup directory...")
    if not check_backup_directory(backup_path):
        update_status("Error: Invalid backup directory")
        return

    # Load Manifest.plist file
    update_status("Loading Manifest.plist file...")
    manifest_data = load_manifest_plist(backup_path)
    if not manifest_data:
        update_status("Error: Manifest.plist file not found")
        messagebox.showwarning("Warning", "Manifest.plist file could not be found.")
        return

    # Check if the backup is encrypted and requires a password
    if manifest_data.get("IsEncrypted", False) and not enable_pw_var.get():
        update_status("Error: Password required")
        messagebox.showerror("Error", "This backup is encrypted. Please enter the password.")
        return

    # Decrypt the backup if required
    if enable_pw_var.get():
        update_status("Decrypting backup...")
        if not decrypt_backup(backup_path, password):
            update_status("Error: Failed to decrypt backup")
            messagebox.showerror("Error", "Failed to decrypt the backup!")
            return

    # Load file information from Manifest.db
    update_status("Loading Manifest.db file...")
    file_info_list = load_manifest_db(backup_path)
    if not file_info_list:
        update_status("Error: Manifest.db file not found")
        messagebox.showwarning("Warning", "Manifest.db file could not be found.")
        return

    # Build file tree and update UI components
    update_status("Building file tree...")
    file_tree, _ = build_tree(file_info_list)
    
    update_status("Building backup tree...")
    # Use icon dictionary if provided
    if icon_dict:
        path_dict, backup_tree_nodes = build_backup_tree(tree_widget, file_tree, icon_dict)
    else:
        path_dict, backup_tree_nodes = build_backup_tree(tree_widget, file_tree)

    tree_widget.path_dict = path_dict
    tree_widget.backup_tree_nodes = backup_tree_nodes

    # Clear file list
    file_list_tree.delete(*file_list_tree.get_children())

    update_status("Backup loaded successfully")
    messagebox.showinfo("Complete", "Backup has been successfully loaded!")
    # --- 추가: Backup load 성공 시 flag 변수 True ---
    if flag_container is not None:
        flag_container["loaded"] = True
    # ---------------------------------------------
    
def check_backup_directory(backup_path):
    """ Checks if the backup directory is valid. """
    if not backup_path:
        messagebox.showerror("Error", "Please enter the Backup Directory.")
        return False
    if not os.path.isdir(backup_path):
        messagebox.showerror("Error", f"Invalid directory: {backup_path}")
        return False
    return True
