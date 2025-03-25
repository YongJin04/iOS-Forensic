import os
import tkinter as tk
from tkinter import ttk, messagebox
from backup_analyzer.manifest_utils import load_manifest_plist

def show_device_info(backup_path, display_ui=True):
    """
    Reads device information from Manifest.plist and either returns the data or displays it in a window.
    
    Args:
        backup_path (str): Path to the backup directory
        display_ui (bool): If True, shows a UI window. If False, just returns the data
        
    Returns:
        dict: Device information if display_ui is False, None otherwise
    """
    if not backup_path or not os.path.isdir(backup_path):
        if display_ui:
            messagebox.showerror("Error", "Please select a valid Backup Directory.")
        return None

    manifest_data = load_manifest_plist(backup_path)
    if not manifest_data:
        if display_ui:
            messagebox.showerror("Error", "Manifest.plist file not found.")
        return None

    flat_info = flatten_dict(manifest_data)
    core_info = filter_core_info(flat_info)

    if not core_info:
        if display_ui:
            messagebox.showinfo("Info", "No core information found; displaying all information.")
        core_info = flat_info
    
    # Process the core info to make it more readable
    device_info = {}
    for key, value in core_info.items():
        display_key = key
        if key.startswith("Lockdown."):
            display_key = key[len("Lockdown."):]
        
        # Map specific keys to normalized names
        if "DeviceName" in display_key:
            device_info["DeviceName"] = value
        elif "ProductType" in display_key:
            device_info["ProductType"] = value
        elif "ProductVersion" in display_key:
            device_info["ProductVersion"] = value
        elif "SerialNumber" in display_key:
            device_info["SerialNumber"] = value
        elif "InternationalMobileEquipmentIdentity" in display_key:
            device_info["IMEI"] = value
        elif "PhoneNumber" in display_key:
            device_info["PhoneNumber"] = value
        elif "LastBackupDate" in display_key:
            device_info["LastBackupDate"] = value
        elif "IntegratedCircuitCardIdentity" in display_key:
            device_info["ICCID"] = value
        elif "MobileEquipmentIdentifier" in display_key:
            device_info["MEID"] = value
        elif "BluetoothAddress" in display_key:
            device_info["BluetoothAddress"] = value
        elif "WiFiAddress" in display_key:
            device_info["WiFiAddress"] = value
        elif "UniqueIdentifier" in display_key or "UniqueDeviceID" in display_key:
            device_info["UniqueIdentifier"] = value
        elif "BuildVersion" in display_key:
            device_info["BuildVersion"] = value
        else:
            # Store other keys as is
            device_info[display_key] = value
    
    # If we're just returning data, return the processed info
    if not display_ui:
        return device_info
        
    # Otherwise, display the UI
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

    # Display the processed info in the UI
    for key, value in device_info.items():
        tree.insert("", "end", values=(key, value))

    close_button = ttk.Button(info_window, text="Close", command=info_window.destroy)
    close_button.pack(pady=5)
    
    return None

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
        "DisplayName",
        "InternationalMobileEquipmentIdentity",
        "PhoneNumber",
        "IntegratedCircuitCardIdentity",
        "MobileEquipmentIdentifier",
        "BluetoothAddress",
        "WiFiAddress"
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
