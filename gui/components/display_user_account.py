from tkinter import ttk
import sqlite3
from pathlib import Path
import datetime

def apple_absolute_to_datetime(apple_time: float) -> str:
    """Apple Absolute Time → 'YYYY-MM-DD HH:MM:SS' 형식 문자열 반환"""
    APPLE_EPOCH = datetime.datetime(2001, 1, 1)
    dt = APPLE_EPOCH + datetime.timedelta(seconds=apple_time)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def fetch_user_accounts(backup_path: str):
    """Bluetooth 설정 DB → ZACCOUNT 테이블에서 사용자 계정 정보 추출"""
    db_path = Path(backup_path) / "94/943624fd13e27b800cc6d9ce1100c22356ee365c"
    if not db_path.exists():
        return []

    accounts = []
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ZUSERNAME, ZOWNINGBUNDLEID, ZACCOUNTDESCRIPTION, ZIDENTIFIER, ZDATE 
                FROM ZACCOUNT;
            """)
            for row in cursor.fetchall():
                username     = row[0] if row[0] is not None else ""
                owning_id    = row[1] if row[1] is not None else ""
                description  = row[2] if row[2] is not None else ""
                identifier   = row[3] if row[3] is not None else ""
                zdate        = apple_absolute_to_datetime(row[4]) if isinstance(row[4], (int, float)) else ""
                accounts.append((username, owning_id, description, identifier, zdate))
    except Exception as e:
        accounts.append((f"[Error] {e}", "", "", "", ""))
    return accounts

def display_user_account(content_frame, backup_path):
    """User Account - Bluetooth 설정 DB에서 ZACCOUNT 정보 표시"""
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    frame = ttk.Frame(content_frame, style="Card.TFrame", padding=20)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(frame, text="👤 User Account", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 15))

    account_list = fetch_user_accounts(backup_path)

    # Username 유무 기준 정렬: 존재하는 row 먼저
    account_list.sort(key=lambda x: (x[0] == "", x[0]))

    if not account_list:
        ttk.Label(frame, text="No user account data found.", style="CardText.TLabel").pack(anchor="w")
        return

    table_frame = ttk.Frame(frame)
    table_frame.pack(fill="both", expand=True)

    tree = ttk.Treeview(
        table_frame,
        columns=("Username", "OwningID", "Description", "Identifier", "Date"),
        show="headings",
        height=12
    )

    tree.heading("Username", text="Username")
    tree.heading("OwningID", text="Owning Bundle ID")
    tree.heading("Description", text="Description")
    tree.heading("Identifier", text="Identifier")
    tree.heading("Date", text="Date (Apple Time)")

    tree.column("Username", width=160)
    tree.column("OwningID", width=180)
    tree.column("Description", width=180)
    tree.column("Identifier", width=200)
    tree.column("Date", width=160)

    for row in account_list:
        tree.insert("", "end", values=row)

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
