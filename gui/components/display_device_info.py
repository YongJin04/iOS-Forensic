import re
import sqlite3
import datetime
from pathlib import Path
from tkinter import ttk
from artifact_analyzer.device.device_info import show_device_info

def parse_imei(raw_value):
    """입력 문자열에서 15자리 IMEI 번호 추출 (없으면 원본의 좌우 공백 제거 결과 반환)."""
    if isinstance(raw_value, str):
        match = re.search(r'\b\d{15}\b', raw_value)
        if match:
            return match.group().strip()
        return raw_value.strip()
    return raw_value

def parse_phone_number(raw_value):
    """입력 문자열에서 전화번호 형식 (국제전화번호 포함)을 추출."""
    if isinstance(raw_value, str):
        match = re.search(r'(\+?\d[\d\s\-.]+)', raw_value)
        if match:
            return match.group().strip()
        return raw_value.strip()
    return raw_value

def parse_date(raw_value):
    """날짜 형식 문자열 추출."""
    if isinstance(raw_value, str):
        match = re.search(r'(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)', raw_value)
        if match:
            return match.group().strip()
        return raw_value.strip()
    return raw_value

def display_device_info(content_frame, backup_path):
    """Display device information in the content frame."""
    for widget in content_frame.winfo_children():
        widget.destroy()

    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill="x", pady=(0, 10))

    ttk.Label(header_frame, text="📱 Device Information", style="ContentHeader.TLabel").pack(side="left")
    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))

    try:
        info_data = show_device_info(backup_path, display_ui=False)

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

        basic_info_frame = ttk.Frame(info_card)
        basic_info_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(basic_info_frame, text="Basic Information", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))

        info_grid = ttk.Frame(basic_info_frame)
        info_grid.pack(fill="x")

        info_items = [
            {"label": "Device Name", "value": info_data.get("DeviceName", "Unknown")},
            {"label": "Device Model", "value": info_data.get("ProductType", "Unknown")},
            {"label": "iOS Version", "value": info_data.get("ProductVersion", "Unknown")},
            {"label": "Serial Number", "value": info_data.get("SerialNumber", "Unknown")},
            #{"label": "IMEI", "value": parse_imei(info_data.get("IMEI", "Unknown"))},
            {"label": "Phone Number", "value": parse_phone_number(info_data.get("PhoneNumber", "Unknown"))},
            #{"label": "Last Backup Date", "value": parse_date(info_data.get("LastBackupDate", "Unknown"))},
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

        additional_keys = ["ICCID", "MEID", "BluetoothAddress", "WiFiAddress", "UniqueIdentifier", "BuildVersion"]
        add_items = []

        for key in additional_keys:
            if key in info_data and info_data[key] != "Unknown":
                display_key = key
                if key == "BluetoothAddress":
                    display_key = "Bluetooth MAC"
                elif key == "WiFiAddress":
                    display_key = "WiFi MAC"
                elif key == "UniqueIdentifier":
                    display_key = "Unique Identifier"
                elif key == "BuildVersion":
                    display_key = "Build Version"

                add_items.append({
                    "label": display_key,
                    "value": info_data[key]
                })

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

    except Exception as e:
        display_error_message(content_frame, f"An error occurred while loading device information: {str(e)}")

def display_error_message(content_frame, message):
    """Display error message."""
    error_frame = ttk.Frame(content_frame, style="ErrorCard.TFrame", padding=15)
    error_frame.pack(fill="both", expand=True, padx=5, pady=5)

    ttk.Label(error_frame, text="", font=("Arial", 24)).pack(pady=(0, 10))
    ttk.Label(error_frame, text=message, style="ErrorText.TLabel", wraplength=400).pack()

def apple_absolute_to_datetime(apple_time: float) -> str:
    """Apple Absolute Time → 'YYYY-MM-DD HH:MM:SS' 형식 문자열 반환"""
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
