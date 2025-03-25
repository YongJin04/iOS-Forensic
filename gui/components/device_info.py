from tkinter import ttk
from artifact_analyzer.device.device_info import show_device_info


def display_device_info(content_frame, backup_path):
    """디바이스 정보를 콘텐츠 프레임에 표시합니다."""
    # 기존 위젯 삭제
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    # 헤더 추가
    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill="x", pady=(0, 10))
    
    ttk.Label(header_frame, text="📱 디바이스 정보", style="ContentHeader.TLabel").pack(side="left")
    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))
    
    try:
        # show_device_info에서 데이터만 가져옴 (UI 표시 없이)
        info_data = show_device_info(backup_path, display_ui=False)
        
        if not info_data:
            display_error_message(content_frame, "디바이스 정보를 찾을 수 없습니다.")
            return
        
        # 정보 카드 생성
        info_card = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
        info_card.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 기본 정보 섹션
        basic_info_frame = ttk.Frame(info_card)
        basic_info_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(basic_info_frame, text="기본 정보", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
        
        # 정보 표시를 위한 그리드
        info_grid = ttk.Frame(basic_info_frame)
        info_grid.pack(fill="x")
        
        # 디바이스 기본 정보 표시
        info_items = [
            {"label": "기기 이름", "value": info_data.get("DeviceName", "알 수 없음")},
            {"label": "기기 모델", "value": info_data.get("ProductType", "알 수 없음")},
            {"label": "iOS 버전", "value": info_data.get("ProductVersion", "알 수 없음")},
            {"label": "일련번호", "value": info_data.get("SerialNumber", "알 수 없음")},
            {"label": "IMEI", "value": info_data.get("IMEI", "알 수 없음")},
            {"label": "전화번호", "value": info_data.get("PhoneNumber", "알 수 없음")},
            {"label": "마지막 백업 날짜", "value": info_data.get("LastBackupDate", "알 수 없음")}
        ]
        
        # 그리드에 정보 추가
        for i, item in enumerate(info_items):
            row = i // 2
            col = i % 2 * 2
            
            # 레이블
            label_frame = ttk.Frame(info_grid)
            label_frame.grid(row=row, column=col, sticky="w", padx=(0, 10), pady=5)
            ttk.Label(label_frame, text=item["label"] + ":", style="InfoLabel.TLabel").pack(anchor="w")
            
            # 값
            value_frame = ttk.Frame(info_grid)
            value_frame.grid(row=row, column=col+1, sticky="w", padx=(0, 20), pady=5)
            ttk.Label(value_frame, text=item["value"], style="InfoValue.TLabel").pack(anchor="w")
        
        # 추가 정보 섹션 (있는 경우)
        additional_keys = ["ICCID", "MEID", "BluetoothAddress", "WiFiAddress", "UniqueIdentifier", "BuildVersion"]
        add_items = []
        
        for key in additional_keys:
            if key in info_data and info_data[key] != "알 수 없음":
                display_key = key
                if key == "BluetoothAddress": display_key = "Bluetooth MAC"
                elif key == "WiFiAddress": display_key = "WiFi MAC"
                elif key == "UniqueIdentifier": display_key = "고유 식별자"
                elif key == "BuildVersion": display_key = "빌드 버전"
                
                add_items.append({
                    "label": display_key, 
                    "value": info_data[key]
                })
        
        # 추가 정보가 있으면 섹션 표시
        if add_items:
            ttk.Separator(info_card, orient="horizontal").pack(fill="x", pady=15)
            
            additional_frame = ttk.Frame(info_card)
            additional_frame.pack(fill="x")
            
            ttk.Label(additional_frame, text="추가 정보", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
            
            # 추가 정보 그리드
            add_info_grid = ttk.Frame(additional_frame)
            add_info_grid.pack(fill="x")
            
            # 그리드에 추가 정보 추가
            for i, item in enumerate(add_items):
                row = i // 2
                col = i % 2 * 2
                
                # 레이블
                label_frame = ttk.Frame(add_info_grid)
                label_frame.grid(row=row, column=col, sticky="w", padx=(0, 10), pady=5)
                ttk.Label(label_frame, text=item["label"] + ":", style="InfoLabel.TLabel").pack(anchor="w")
                
                # 값
                value_frame = ttk.Frame(add_info_grid)
                value_frame.grid(row=row, column=col+1, sticky="w", padx=(0, 20), pady=5)
                ttk.Label(value_frame, text=item["value"], style="InfoValue.TLabel").pack(anchor="w")
    
    except Exception as e:
        display_error_message(content_frame, f"디바이스 정보를 로드하는 중 오류가 발생했습니다: {str(e)}")

def display_error_message(content_frame, message):
    """오류 메시지를 표시합니다."""
    # 오류 메시지 프레임
    error_frame = ttk.Frame(content_frame, style="ErrorCard.TFrame", padding=15)
    error_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 오류 아이콘과 메시지
    ttk.Label(error_frame, text="⚠️", font=("Arial", 24)).pack(pady=(0, 10))
    ttk.Label(error_frame, text=message, style="ErrorText.TLabel", wraplength=400).pack()