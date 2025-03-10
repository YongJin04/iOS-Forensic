from tkinter import messagebox
import os

from backup_analyzer.manifest_utils import load_manifest_plist, load_manifest_db
from backup_analyzer.build_tree_utils import build_tree, build_backup_tree
from backup_analyzer.backup_decrypt_utils import decrypt_backup

def load_backup(backup_path, password, tree_widget, enable_pw_var, file_list_tree):
    """ Loads the backup data and updates the UI components. """
    if not check_backup_directory(backup_path):
        return

    # Load Manifest.plist file
    manifest_data = load_manifest_plist(backup_path)
    if not manifest_data:
        messagebox.showwarning("Warning", "Could not find the Manifest.plist file.")
        return

    # Check if the backup is encrypted and requires a password
    if manifest_data.get("IsEncrypted", False) and not enable_pw_var.get():
        messagebox.showerror("Error", "This backup is encrypted. Please enter a password.")
        return

    # Decrypt the backup if required
    if enable_pw_var.get():
        if not decrypt_backup(backup_path, password):
            messagebox.showerror("Error", "Backup decryption failed!")
            return

    # Load file information from Manifest.db
    file_info_list = load_manifest_db(backup_path)
    if not file_info_list:
        messagebox.showwarning("Warning", "Could not find the Manifest.db file.")
        return

    # Build file tree and update UI components
    file_tree, _ = build_tree(file_info_list)
    path_dict, backup_tree_nodes = build_backup_tree(tree_widget, file_tree)

    tree_widget.path_dict = path_dict
    tree_widget.backup_tree_nodes = backup_tree_nodes

    file_list_tree.delete(*file_list_tree.get_children())

    messagebox.showinfo("Complete", "Backup Load Complete!")

def check_backup_directory(backup_path):
    """ Checks if the backup directory is valid. """
    if not backup_path:
        messagebox.showerror("Error", "Please enter the Backup Directory.")
        return False
    if not os.path.isdir(backup_path):
        messagebox.showerror("Error", f"Invalid directory: {backup_path}")
        return False
    return True


