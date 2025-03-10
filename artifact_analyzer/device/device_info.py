from tkinter import ttk, messagebox
import tkinter as tk
import os

from backup_analyzer.manifest_utils import load_manifest_plist

def show_device_info(backup_path):
    """ Reads device information from Manifest.plist in the backup path and displays it in a new window. """
    if not backup_path or not os.path.isdir(backup_path):
        messagebox.showerror("Error", "Please select a valid Backup Directory.")
        return

    manifest_data = load_manifest_plist(backup_path)
    if not manifest_data:
        messagebox.showerror("Error", "Manifest.plist file not found.")
        return

    flat_info = flatten_dict(manifest_data)
    core_info = filter_core_info(flat_info)

    if not core_info:
        messagebox.showinfo("Info", "No core information found; displaying all information.")
        core_info = flat_info

    info_window = tk.Toplevel()
    info_window.title("Device Info")
    info_window.geometry("600x400")

    tree = ttk.Treeview(info_window, columns=("Property", "Value"), show="headings")
    tree.heading("Property", text="Property")
    tree.heading("Value", text="Value")
    tree.column("Property", width=200, anchor="w")
    tree.column("Value", width=380, anchor="w")

    scrollbar = ttk.Scrollbar(info_window, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    for key, value in core_info.items():
        display_key = key
        if key.lower().startswith("lockdown."):
            display_key = key[len("Lockdown."):]
        tree.insert("", "end", values=(display_key, value))

    close_button = ttk.Button(info_window, text="Close", command=info_window.destroy)
    close_button.pack(pady=5)

def filter_core_info(flat_info):
    """ Filters the flattened dictionary for specified core keys that represent essential device information. """
    core_keys = [
        "DeviceName",
        "UniqueIdentifier",
        "UniqueDeviceID",
        "ProductType",
        "ProductVersion",
        "BuildVersion",
        "SerialNumber",
        "LastBackupDate",
        "IsEncrypted",
        "DisplayName"
    ]
    filtered_info = {}

    def normalize(s):
        return s.replace(" ", "").replace(".", "").lower()

    for key, value in flat_info.items():
        norm_key = normalize(key)
        for core in core_keys:
            if core.lower() in norm_key:
                filtered_info[key] = value
                break
    return filtered_info

def flatten_dict(d, parent_key='', sep='.'):
    """ Flattens a nested dictionary into a single-level dictionary with concatenated keys. """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, ', '.join(map(str, v))))
        else:
            items.append((new_key, v))
    return dict(items)
