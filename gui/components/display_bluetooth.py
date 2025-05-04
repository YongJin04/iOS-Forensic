from tkinter import ttk
import sqlite3
from pathlib import Path
import datetime

def apple_absolute_to_datetime(apple_time: float) -> str:
    """Apple Absolute Time → 'YYYY-MM-DD HH:MM:SS' 형식 문자열 반환"""
    APPLE_EPOCH = datetime.datetime(2001, 1, 1)
    dt = APPLE_EPOCH + datetime.timedelta(seconds=apple_time)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def clean_address(address: str) -> str:
    """'Random XX:XX:...' → 'XX:XX:...' 형태로 정제"""
    if isinstance(address, str):
        parts = address.strip().split()
        return parts[-1] if len(parts) > 0 else address
    return address

def fetch_bluetooth_devices(backup_path: str):
    """Bluetooth.db → OtherDevices 테이블에서 Uuid, Name, Address, LastSeenTime 추출"""
    db_path = Path(backup_path) / "3a/3afe56e2c5aa8c090ded49445d95e8769ef34899"
    if not db_path.exists():
        return []

    results = []
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT Uuid, Name, Address, LastSeenTime FROM OtherDevices;")
            rows = cursor.fetchall()
            for row in rows:
                uuid = row[0]
                name = row[1]
                address = clean_address(row[2])
                last_seen = row[3] if isinstance(row[3], (int, float)) else "Unknown"
                results.append((uuid, name, address, last_seen))
    except Exception as e:
        results.append(("Error", str(e), "", ""))
    return results

def display_bluetooth(content_frame, backup_path):
    """Bluetooth 분석 결과 표시 (OtherDevices 테이블 기반)"""
    for widget in content_frame.winfo_children():
        widget.destroy()

    frame = ttk.Frame(content_frame, style="Card.TFrame", padding=20)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(frame, text="🔵 Paired Bluetooth Devices", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 15))

    # Bluetooth 정보 추출 및 정렬 (Name 있는 항목 우선)
    device_list = fetch_bluetooth_devices(backup_path)
    device_list.sort(key=lambda x: (x[1] is None or x[1] == "", x[1]))  # Name이 없으면 뒤로 정렬

    if not device_list:
        ttk.Label(frame, text="No Bluetooth devices found.", style="CardText.TLabel").pack(anchor="w")
        return

    # 테이블 + 스크롤 생성
    table_frame = ttk.Frame(frame)
    table_frame.pack(fill="both", expand=True)

    tree = ttk.Treeview(
        table_frame,
        columns=("UUID", "Name", "Address", "LastSeen"),
        show="headings",
        height=12
    )

    # 컬럼 헤더 정의
    tree.heading("UUID", text="UUID")
    tree.heading("Name", text="Device Name")
    tree.heading("Address", text="MAC Address")
    tree.heading("LastSeen", text="Last Seen")

    # 컬럼 크기 조정 (UUID 넓힘)
    tree.column("UUID", width=240)       # ← 기존보다 넓게
    tree.column("Name", width=160)
    tree.column("Address", width=130)
    tree.column("LastSeen", width=160)

    # 데이터 삽입
    for row in device_list:
        tree.insert("", "end", values=row)

    # 스크롤바 추가
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
