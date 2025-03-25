from tkinter import filedialog

from backup_analyzer.manifest_utils import load_manifest_plist
from backup_analyzer.build_file_list_utils import build_file_list_tree

def browse_backup_path(path_var, password_entry, password_var, enable_pw_var):  # Button: "Browse"
    """ Opens a file dialog to select a backup folder and checks encryption status. """
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        path_var.set(folder_selected)
        manifest_data = load_manifest_plist(folder_selected)
        is_encrypted = manifest_data.get("IsEncrypted", False)

        if is_encrypted:
            enable_pw_var.set(1)
            password_entry.config(state="normal")
        else:
            enable_pw_var.set(0)
            password_entry.config(state="disabled")
            password_var.set("")

def toggle_password_entry(enable_pw_var, password_entry, password_var):  # Button: "Enable Password"
    """ Enables or disables the password entry field based on encryption status. """
    if enable_pw_var.get():
        password_entry.config(state="normal")
    else:
        password_entry.config(state="disabled")
        password_var.set("")

def update_file_list_from_backup_tree_click(event, file_list_tree, tree_widget):  # "Backup Tree" Event: "One Clicked"
    """ Handles selection in the backup tree and updates the file list. """
    selected_item = tree_widget.selection()
    if not selected_item:
        return

    values = tree_widget.item(selected_item[0], "values")
    if not values:
        return

    full_path = values[0]

    file_list_tree.delete(*file_list_tree.get_children())

    sub_dict = tree_widget.path_dict.get(full_path, {})
    build_file_list_tree(file_list_tree, sub_dict, parent="", full_path=full_path)

def update_backup_tree_from_file_list_double_click(event, file_list_tree, tree_widget):  # "File List" Event: "Double Clicked"
    """ Selects and expands the corresponding node in the backup tree when a file is double-clicked. """
    selected_item = file_list_tree.selection()
    if not selected_item:
        return

    values = file_list_tree.item(selected_item[0], "values")
    if not values:
        return

    full_path = values[0]
    subtree = tree_widget.path_dict.get(full_path)
    if not subtree:
        return

    node_id = tree_widget.backup_tree_nodes.get(full_path)
    if node_id:
        tree_widget.selection_set(node_id)
        tree_widget.focus(node_id)
        tree_widget.item(node_id, open=True)
        tree_widget.see(node_id)
