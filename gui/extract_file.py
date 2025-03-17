from tkinter import filedialog
import tkinter as tk
import sqlite3
import shutil
import os

def show_file_list_context_menu(event, file_list_tree, backup_path):
    """ Show context menu on right-click in File List Treeview. """
    row_id = file_list_tree.identify_row(event.y)  # Identify which row was clicked
    if not row_id:
        return  # Exit if click was not on a valid row

    file_list_tree.selection_set(row_id)  # Select the clicked row
    file_list_tree.focus(row_id)          # Set focus to the clicked row

    # Create context menu
    menu = tk.Menu(file_list_tree, tearoff=0)
    # Add "Extract" option to context menu (calls extract_file function)
    menu.add_command(
        label="Extract",
        command=lambda: extract_file(file_list_tree, backup_path)
    )
    # Display context menu at mouse click position
    menu.post(event.x_root, event.y_root)


def extract_file(file_list_tree, backup_path):
    """ Extract selected file from backup based on Manifest.db info. """
    selected_item = file_list_tree.selection()  # Get selected row
    if not selected_item:
        return  # Exit if no selection

    file_values = file_list_tree.item(selected_item[0], "values")  # Retrieve file data
    if not file_values:
        return  # Exit if no file data found

    ios_path = "/".join(file_values[0].split('/')[1:])
    print("[Extract] iOS path:", ios_path)

    parts = ios_path.split("/")
    if len(parts) < 2:
        print("  -> Failed to parse iOS path.")
        return

    # Parse iOS path into domain and relative path
    domain = parts[0]
    relative_path = "/".join(parts[1:])
    if not domain or not relative_path:
        print("  -> Failed to parse iOS path.")
        return

    # Lookup fileID using domain & relative path from Manifest.db
    file_id = lookup_fileID_in_manifest(backup_path, domain, relative_path)
    if not file_id:
        print("  -> Failed to find fileID in Manifest DB.")
        return

    # Log extracted details
    print(f"  -> Domain: {domain}")
    print(f"  -> relativePath: {relative_path}")
    print(f"  -> Found fileID (SHA1): {file_id}")

    # Construct local backup file path
    subdir = file_id[:2]  # First two characters used as subdirectory
    local_backup_file = os.path.join(backup_path, subdir, file_id)
    abs_local_backup_file = os.path.abspath(local_backup_file)
    print("[Extract] Local backup file path:", abs_local_backup_file)

    # Suggest filename based on original relative path
    filename_suggestion = os.path.basename(relative_path).lower()

    # Open file save dialog for user to choose where to save extracted file
    initialdir = os.path.expanduser("~")
    save_path = filedialog.asksaveasfilename(
        title="Select save location for extracted file",
        defaultextension="",
        initialdir=initialdir,
        initialfile=filename_suggestion,
        filetypes=[("All Files", "*.*")]
    )

    if not save_path:
        print("[Extract] User canceled")
        return

    # Attempt to copy backup file to selected save location
    try:
        shutil.copy2(abs_local_backup_file, save_path)
        print(f"[Extract] File copied to:\n  {save_path}")
    except Exception as e:
        print(f"[Extract] Error copying file: {e}")

def lookup_fileID_in_manifest(backup_path, domain, relative_path):
    """ Query Manifest.db to retrieve fileID based on domain and relative path. """
    manifest_db = os.path.join(backup_path, "Manifest.db")
    if not os.path.exists(manifest_db):
        print("  -> Manifest.db file not found.")
        return None

    try:
        # Connect to SQLite database
        conn = sqlite3.connect(manifest_db)
        c = conn.cursor()
        # SQL query to find matching fileID
        query = """
        SELECT fileID
          FROM Files
         WHERE domain = ?
           AND relativePath = ?
         LIMIT 1
        """
        c.execute(query, (domain, relative_path))
        row = c.fetchone()
        conn.close()

        if row:
            return row[0]  # Return fileID if found
        else:
            return None  # No match found
    except Exception as e:
        print("  -> Error querying Manifest.db:", e)
        return None
