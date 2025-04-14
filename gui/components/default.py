from tkinter import ttk

def display_bluetooth(content_frame, backup_path):
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    frame = ttk.Frame(content_frame, style="Card.TFrame", padding=20)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(frame, text="🔵 Bluetooth Devices", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))
    ttk.Label(frame, text="Bluetooth 관련 정보 분석 결과가 여기에 표시됩니다.", style="CardText.TLabel").pack(anchor="w")


"""
아래의 코드에서 
from tkinter import ttk

def display_user_account(content_frame, backup_path):
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    frame = ttk.Frame(content_frame, style="Card.TFrame", padding=20)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(frame, text="👤 User Account", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))
    ttk.Label(frame, text="Bluetooth 관련 정보 분석 결과가 여기에 표시됩니다.", style="CardText.TLabel").pack(anchor="w")

아래의 조건에 맞게 코드를 추가하여 작성해줘.
해당 Bluetooth 파일에서 backup_path 이하의 "94/943624fd13e27b800cc6d9ce1100c22356ee365c" 파일이 SQLite파일인데, 해당 SQLite 파일에서 "ZACCOUNT" Table에서 각 row의 ZIDENTIFIER, ZUSERNAME, ZDATE을 가져와줘. 이때, ZDATE는 Apple Absolated Time을 사용해주고, 해당 정보를 DB Table처럼 View하는 기능도 추가해줘.
"""