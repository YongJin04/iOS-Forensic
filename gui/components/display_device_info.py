import re
import sqlite3
import datetime
import plistlib
from pathlib import Path
from tkinter import ttk
from artifact_analyzer.device.device_info import show_device_info

def parse_imei(raw_value):
    if isinstance(raw_value, str):
        match = re.search(r'\b\d{15}\b', raw_value)
        if match:
            return match.group().strip()
        return raw_value.strip()
    return raw_value

def parse_phone_number(raw_value):
    if isinstance(raw_value, str):
        match = re.search(r'(\+?\d[\d\s\-.]+)', raw_value)
        if match:
            return match.group().strip()
        return raw_value.strip()
    return raw_value

def parse_date(raw_value):
    if isinstance(raw_value, str):
        match = re.search(r'(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)', raw_value)
        if match:
            return match.group().strip()
        return raw_value.strip()
    return raw_value

def apple_absolute_to_datetime(apple_time: float) -> str:
    APPLE_EPOCH = datetime.datetime(2001, 1, 1)
    dt = APPLE_EPOCH + datetime.timedelta(seconds=apple_time)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def extract_subscriber_info(backup_path) -> tuple[str, str] | None:
    backup_path = Path(backup_path)
    db_path = backup_path / "ed/ed1f8fb5a948b40504c19580a458c384659a605e"
    if not db_path.exists():
        print(f"[!] DB 파일이 존재하지 않습니다: {db_path}")
        return None

    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT subscriber_mdn, last_update_time FROM subscriber_info LIMIT 1;")
            row = cursor.fetchone()
            if row:
                PhoneNumber = row[0]
                LastUpdateTime = apple_absolute_to_datetime(row[1])
                return PhoneNumber, LastUpdateTime
            else:
                print("[!] subscriber_info 테이블에 데이터가 없습니다.")
                return None
    except Exception as e:
        print(f"[!] DB 읽기 실패: {e}")
        return None

def load_info_plist(backup_path):
    keys_of_interest = [
        "Build Version", "Device Name", "Display Name", "GUID", "ICCID",
        "IMEI", "IMEI 2", "Installed Applications", "Last Backup Date",
        "Phone Number", "Product Name", "Product Type", "Product Version",
        "Serial Number", "Target Identifier", "Target Type", "Unique Identifier"
    ]

    plist_path = Path(backup_path) / "info.plist"
    if not plist_path.exists():
        print(f"[!] info.plist 파일이 존재하지 않습니다: {plist_path}")
        return {}

    try:
        with open(plist_path, 'rb') as fp:
            plist_data = plistlib.load(fp)
    except Exception as e:
        print(f"[!] info.plist 파싱 실패: {e}")
        return {}

    result = {}
    for key in keys_of_interest:
        value = plist_data.get(key)
        if value is not None:
            if key == "Installed Applications" and isinstance(value, list):
                result[key] = [str(app) for app in value]
            elif isinstance(value, bytes):
                result[key] = value.hex()
            else:
                result[key] = str(value)
    return result

def count_files_with_flag(backup_path) -> int:
    db_path = Path(backup_path) / "manifest.db"
    if not db_path.exists():
        print(f"[!] manifest.db가 존재하지 않습니다: {db_path}")
        return 0
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Files WHERE flags != 2;")
            count = cursor.fetchone()[0]
            return count
    except Exception as e:
        print(f"[!] manifest.db 읽기 실패: {e}")
        return 0

def get_directory_size(path: Path) -> int:
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total

def display_device_info(content_frame, backup_path):
    for widget in content_frame.winfo_children():
        widget.destroy()

    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill="x", pady=(0, 10))
    ttk.Label(header_frame, text="📱 Device Information", style="ContentHeader.TLabel").pack(side="left")
    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))

    try:
        info_data = show_device_info(backup_path, display_ui=False)
        plist_info = load_info_plist(backup_path)
        info_data.update(plist_info)

        result = extract_subscriber_info(backup_path)
        if result:
            PhoneNumber, LastUpdateTime = result
            info_data["PhoneNumber"] = PhoneNumber
            info_data["LastUpdateTime"] = LastUpdateTime

        if not info_data:
            display_error_message(content_frame, "Device information not found.")
            return

        info_card = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
        info_card.pack(fill="both", expand=True, padx=5, pady=5)

        # Basic Information
        basic_info_frame = ttk.Frame(info_card)
        basic_info_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(basic_info_frame, text="Basic Information", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
        info_grid = ttk.Frame(basic_info_frame)
        info_grid.pack(fill="x")

        info_items = [
            {"label": "Device Name", "value": info_data.get("Device Name", info_data.get("DeviceName", "Unknown"))},
            {"label": "Device Model", "value": info_data.get("Product Type", info_data.get("ProductType", "Unknown"))},
            {"label": "iOS Version", "value": info_data.get("Product Version", info_data.get("ProductVersion", "Unknown"))},
            {"label": "Phone Number", "value": parse_phone_number(info_data.get("Phone Number", info_data.get("PhoneNumber", "Unknown")))},
            {"label": "Serial Number", "value": info_data.get("Serial Number", info_data.get("SerialNumber", "Unknown"))},
            {"label": "IMEI", "value": parse_imei(info_data.get("IMEI", "Unknown"))},
            {"label": "Last Backup Date", "value": parse_date(info_data.get("Last Backup Date", "Unknown"))},
            {"label": "Last Update Time", "value": info_data.get("LastUpdateTime", "Unknown")}
        ]

        for i, item in enumerate(info_items):
            row = i // 2
            col = (i % 2) * 2
            label_frame = ttk.Frame(info_grid)
            label_frame.grid(row=row, column=col, sticky="w", padx=(0, 10), pady=5)
            ttk.Label(label_frame, text=item["label"] + ":", style="InfoLabel.TLabel").pack(anchor="w")
            value_frame = ttk.Frame(info_grid)
            value_frame.grid(row=row, column=col + 1, sticky="w", padx=(0, 20), pady=5)
            ttk.Label(value_frame, text=item["value"], style="InfoValue.TLabel").pack(anchor="w")

        # Additional Information
        additional_keys = [
            "ICCID", "GUID", "Display Name", "Product Name",
            "Target Identifier", "Unique Identifier", "Target Type", "Build Version"
        ]
        add_items = []
        for key in additional_keys:
            if key in info_data and info_data[key] != "Unknown":
                add_items.append({"label": key, "value": info_data[key]})

        if add_items:
            ttk.Separator(info_card, orient="horizontal").pack(fill="x", pady=15)
            additional_frame = ttk.Frame(info_card)
            additional_frame.pack(fill="x")
            ttk.Label(additional_frame, text="Additional Information", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
            add_info_grid = ttk.Frame(additional_frame)
            add_info_grid.pack(fill="x")

            for i, item in enumerate(add_items):
                row = i // 2
                col = (i % 2) * 2
                label_frame = ttk.Frame(add_info_grid)
                label_frame.grid(row=row, column=col, sticky="w", padx=(0, 10), pady=5)
                ttk.Label(label_frame, text=item["label"] + ":", style="InfoLabel.TLabel").pack(anchor="w")
                value_frame = ttk.Frame(add_info_grid)
                value_frame.grid(row=row, column=col + 1, sticky="w", padx=(0, 20), pady=5)
                ttk.Label(value_frame, text=item["value"], style="InfoValue.TLabel").pack(anchor="w")

        # 🖼 Image Information
        num_files = count_files_with_flag(backup_path)
        image_size = get_directory_size(Path(backup_path))

        ttk.Separator(info_card, orient="horizontal").pack(fill="x", pady=15)
        image_info_frame = ttk.Frame(info_card)
        image_info_frame.pack(fill="x")
        ttk.Label(image_info_frame, text="🖼 Image Information", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
        image_info_grid = ttk.Frame(image_info_frame)
        image_info_grid.pack(fill="x")

        image_info_items = [
            {"label": "Number of Files", "value": f"{num_files:,}"},
            {"label": "Size of Image", "value": format_size(image_size)}
        ]

        for i, item in enumerate(image_info_items):
            row = i // 2
            col = (i % 2) * 2
            label_frame = ttk.Frame(image_info_grid)
            label_frame.grid(row=row, column=col, sticky="w", padx=(0, 10), pady=5)
            ttk.Label(label_frame, text=item["label"] + ":", style="InfoLabel.TLabel").pack(anchor="w")
            value_frame = ttk.Frame(image_info_grid)
            value_frame.grid(row=row, column=col + 1, sticky="w", padx=(0, 20), pady=5)
            ttk.Label(value_frame, text=item["value"], style="InfoValue.TLabel").pack(anchor="w")

    except Exception as e:
        display_error_message(content_frame, f"An error occurred while loading device information: {str(e)}")

def display_error_message(content_frame, message):
    error_frame = ttk.Frame(content_frame, style="ErrorCard.TFrame", padding=15)
    error_frame.pack(fill="both", expand=True, padx=5, pady=5)
    ttk.Label(error_frame, text="", font=("Arial", 24)).pack(pady=(0, 10))
    ttk.Label(error_frame, text=message, style="ErrorText.TLabel", wraplength=400).pack()

def format_size(size_bytes):
    """바이트 단위 크기를 GB/MB/KB/Bytes 중 적절한 단위로 변환"""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024 ** 3):.2f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} Bytes"