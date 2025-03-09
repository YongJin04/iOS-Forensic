# gui/device_info.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
from backup_analyzer.manifest_utils import load_manifest_plist

def flatten_dict(d, parent_key='', sep='.'):
    """
    중첩된 딕셔너리를 평탄화하는 함수.
    예: {'a': {'b': 1}} -> {'a.b': 1}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # 리스트는 콤마로 구분된 문자열로 변환
            items.append((new_key, ', '.join(map(str, v))))
        else:
            items.append((new_key, v))
    return dict(items)

def filter_core_info(flat_info):
    """
    중요한 핵심 정보만 필터링.
    주요 키: DeviceName, UniqueIdentifier(또는 UniqueDeviceID), ProductType, ProductVersion,
           BuildVersion, SerialNumber, LastBackupDate, IsEncrypted, DisplayName
    """
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
        # 공백과 구분자(.) 제거 후 소문자 변환
        return s.replace(" ", "").replace(".", "").lower()

    for key, value in flat_info.items():
        norm_key = normalize(key)
        for core in core_keys:
            if core.lower() in norm_key:
                filtered_info[key] = value
                break
    return filtered_info

def show_device_info(backup_path):
    """
    backup_path에서 Manifest.plist를 읽어, 
    중요한 핵심 정보만 필터링하여 새로운 창에서 표 형태로 표시하는 함수.
    출력 시 "LockDown." 접두어가 있다면 이를 제거함.
    """
    if not backup_path or not os.path.isdir(backup_path):
        messagebox.showerror("Error", "유효한 Backup Directory를 선택해주세요.")
        return

    manifest_data = load_manifest_plist(backup_path)
    if not manifest_data:
        messagebox.showerror("Error", "Manifest.plist 파일을 찾을 수 없습니다.")
        return

    # Manifest 데이터를 평탄화 후, 핵심 정보만 필터링
    flat_info = flatten_dict(manifest_data)
    core_info = filter_core_info(flat_info)

    # 필터링된 결과가 없으면 전체 정보를 사용하도록 함.
    if not core_info:
        messagebox.showinfo("Info", "핵심 정보가 존재하지 않아 전체 정보를 표시합니다.")
        core_info = flat_info

    # 새로운 Toplevel 창 생성
    info_window = tk.Toplevel()
    info_window.title("Device Info")
    info_window.geometry("600x400")

    # Treeview를 사용해 표 형태로 정보 표시 (Property, Value)
    tree = ttk.Treeview(info_window, columns=("Property", "Value"), show="headings")
    tree.heading("Property", text="Property")
    tree.heading("Value", text="Value")
    tree.column("Property", width=200, anchor="w")
    tree.column("Value", width=380, anchor="w")

    # 수직 스크롤바 추가
    scrollbar = ttk.Scrollbar(info_window, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    # 필터링된 핵심 정보 삽입 (출력 시 "LockDown." 접두어 제거)
    for key, value in core_info.items():
        display_key = key
        if key.lower().startswith("lockdown."):
            display_key = key[len("Lockdown."):]
        tree.insert("", "end", values=(display_key, value))

    # 닫기 버튼 추가
    close_button = ttk.Button(info_window, text="Close", command=info_window.destroy)
    close_button.pack(pady=5)
