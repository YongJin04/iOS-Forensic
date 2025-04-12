import re
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
        # 예시 패턴: +82 10-1234-5678 또는 010-1234-5678 등 (숫자, 공백, -, . 허용)
        match = re.search(r'(\+?\d[\d\s\-.]+)', raw_value)
        if match:
            return match.group().strip()
        return raw_value.strip()
    return raw_value

def parse_date(raw_value):
    """입력 문자열에서 YYYY-MM-DD 또는 YYYY-MM-DD hh:mm:ss 형식의 날짜 추출."""
    if isinstance(raw_value, str):
        match = re.search(r'(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)', raw_value)
        if match:
            return match.group().strip()
        return raw_value.strip()
    return raw_value

def display_device_info(content_frame, backup_path):
    """Display device information in the content frame."""
    # Remove existing widgets
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    # Add header
    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill="x", pady=(0, 10))
    
    ttk.Label(header_frame, text="📱 Device Information", style="ContentHeader.TLabel").pack(side="left")
    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))
    
    try:
        # Fetch data only from show_device_info (without displaying UI)
        info_data = show_device_info(backup_path, display_ui=False)
        
        if not info_data:
            display_error_message(content_frame, "Device information not found.")
            return
        
        # Create info card
        info_card = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
        info_card.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Basic info section
        basic_info_frame = ttk.Frame(info_card)
        basic_info_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(basic_info_frame, text="Basic Information", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
        
        # Grid for displaying information
        info_grid = ttk.Frame(basic_info_frame)
        info_grid.pack(fill="x")
        
        # Display basic device information
        info_items = [
            {"label": "Device Name", "value": info_data.get("DeviceName", "Unknown")},
            {"label": "Device Model", "value": info_data.get("ProductType", "Unknown")},
            {"label": "iOS Version", "value": info_data.get("ProductVersion", "Unknown")},
            {"label": "Serial Number", "value": info_data.get("SerialNumber", "Unknown")},
            {"label": "IMEI", "value": parse_imei(info_data.get("IMEI", "Unknown"))},
            {"label": "Phone Number", "value": parse_phone_number(info_data.get("PhoneNumber", "Unknown"))},
            {"label": "Last Backup Date", "value": parse_date(info_data.get("LastBackupDate", "Unknown"))}
        ]
        
        # Add information to the grid
        for i, item in enumerate(info_items):
            row = i // 2
            col = (i % 2) * 2
            
            # Label
            label_frame = ttk.Frame(info_grid)
            label_frame.grid(row=row, column=col, sticky="w", padx=(0, 10), pady=5)
            ttk.Label(label_frame, text=item["label"] + ":", style="InfoLabel.TLabel").pack(anchor="w")
            
            # Value
            value_frame = ttk.Frame(info_grid)
            value_frame.grid(row=row, column=col+1, sticky="w", padx=(0, 20), pady=5)
            ttk.Label(value_frame, text=item["value"], style="InfoValue.TLabel").pack(anchor="w")
        
        # Additional info section (if available)
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
        
        # If additional info exists, display section
        if add_items:
            ttk.Separator(info_card, orient="horizontal").pack(fill="x", pady=15)
            
            additional_frame = ttk.Frame(info_card)
            additional_frame.pack(fill="x")
            
            ttk.Label(additional_frame, text="Additional Information", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
            
            # Additional info grid
            add_info_grid = ttk.Frame(additional_frame)
            add_info_grid.pack(fill="x")
            
            # Add additional info to grid
            for i, item in enumerate(add_items):
                row = i // 2
                col = (i % 2) * 2
                
                # Label
                label_frame = ttk.Frame(add_info_grid)
                label_frame.grid(row=row, column=col, sticky="w", padx=(0, 10), pady=5)
                ttk.Label(label_frame, text=item["label"] + ":", style="InfoLabel.TLabel").pack(anchor="w")
                
                # Value
                value_frame = ttk.Frame(add_info_grid)
                value_frame.grid(row=row, column=col+1, sticky="w", padx=(0, 20), pady=5)
                ttk.Label(value_frame, text=item["value"], style="InfoValue.TLabel").pack(anchor="w")
    
    except Exception as e:
        display_error_message(content_frame, f"An error occurred while loading device information: {str(e)}")

def display_error_message(content_frame, message):
    """Display error message."""
    # Error message frame
    error_frame = ttk.Frame(content_frame, style="ErrorCard.TFrame", padding=15)
    error_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Error icon and message
    ttk.Label(error_frame, text="", font=("Arial", 24)).pack(pady=(0, 10))
    ttk.Label(error_frame, text=message, style="ErrorText.TLabel", wraplength=400).pack()
