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
            cursor.execute(
                """
                SELECT ZUSERNAME, ZOWNINGBUNDLEID, ZACCOUNTDESCRIPTION,
                       ZIDENTIFIER, ZDATE
                FROM ZACCOUNT;
                """
            )
            for row in cursor.fetchall():
                username = row[0] or ""
                owning_id = row[1] or ""
                description = row[2] or ""
                identifier = row[3] or ""
                zdate = (
                    apple_absolute_to_datetime(row[4])
                    if isinstance(row[4], (int, float))
                    else ""
                )
                accounts.append((username, owning_id, description, identifier, zdate))
    except Exception as e:
        accounts.append((f"[Error] {e}", "", "", "", ""))
    return accounts


def display_user_account(content_frame, backup_path):
    """User Account - Bluetooth 설정 DB에서 ZACCOUNT 정보 표시 (화면 꽉 채우기 적용)"""
    # 기존에 있던 위젯들 제거
    for widget in content_frame.winfo_children():
        widget.destroy()

    # 상위 프레임: 전체를 채우도록 pack(fill, expand)
    frame = ttk.Frame(content_frame, style="Card.TFrame", padding=20)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    # 헤더
    ttk.Label(frame, text="👤 User Account", style="CardHeader.TLabel").pack(
        anchor="w", pady=(0, 15)
    )

    account_list = fetch_user_accounts(backup_path)

    # Username 유무 기준 정렬: 존재하는 row 먼저
    account_list.sort(key=lambda x: (x[0] == "", x[0]))

    if not account_list:
        ttk.Label(
            frame, text="No user account data found.", style="CardText.TLabel"
        ).pack(anchor="w")
        return

    # ── 트리뷰 & 스크롤바 컨테이너 ───────────────────────────────
    table_frame = ttk.Frame(frame)
    table_frame.pack(fill="both", expand=True)

    # Treeview 생성 (높이(height) 대신, 부모 프레임에 맞춰 늘어나도록 stretch=True 설정)
    tree = ttk.Treeview(
        table_frame,
        columns=("Username", "OwningID", "Description", "Identifier", "Date"),
        show="headings",
    )

    # 헤더
    tree.heading("Username", text="Username")
    tree.heading("OwningID", text="Owning Bundle ID")
    tree.heading("Description", text="Description")
    tree.heading("Identifier", text="Identifier")
    tree.heading("Date", text="Date (Apple Time)")

    # 열 폭: stretch=True 로 변경 (창 크기에 맞춰 자동으로 늘어남)
    tree.column("Username", width=160, stretch=True)      # stretch=True
    tree.column("OwningID", width=180, stretch=True)      # stretch=True
    tree.column("Description", width=180, stretch=True)   # stretch=True
    tree.column("Identifier", width=200, stretch=True)    # stretch=True
    tree.column("Date", width=160, stretch=True)          # stretch=True

    # 스트라이프
    tree.tag_configure("stripe", background="#f5f5f5")

    for idx, row in enumerate(account_list):
        tag = ("stripe",) if idx % 2 else ()
        tree.insert("", "end", values=row, tags=tag)

    # 세로·가로 스크롤바 추가
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # table_frame 내부 그리드 설정: 0번 행/열이 빈틈없이 늘어나도록
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    # Treeview와 Scrollbar 배치 (그리드)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
