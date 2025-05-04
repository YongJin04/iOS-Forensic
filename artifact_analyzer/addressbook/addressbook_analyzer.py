import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------

def format_mac_time(mac_time: float) -> str:
    """
    macOS 기준 시간(2001-01-01 UTC)에서부터 mac_time 초만큼 더해
    한국 표준시(KST)로 변환한 'YYYY년 M월 D일 요일 오전/오후 H:MM:SS GMT±zzzz' 문자열을 반환.
    실패 시 "변환 실패 (mac_time)" 반환.
    """
    try:
        mac_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
        dt = mac_epoch + timedelta(seconds=mac_time)
        kst = dt.astimezone(timezone(timedelta(hours=9)))

        weekdays = {
            0: "월요일", 1: "화요일", 2: "수요일", 3: "목요일",
            4: "금요일", 5: "토요일", 6: "일요일"
        }
        weekday_kor = weekdays[kst.weekday()]
        am_pm = "오전" if kst.strftime("%p") == "AM" else "오후"
        hour = int(kst.strftime("%I"))
        minute = kst.strftime("%M")
        second = kst.strftime("%S")

        return (
            f"{kst.year}년 {kst.month}월 {kst.day}일 {weekday_kor} "
            f"{am_pm} {hour}:{minute}:{second} GMT{kst.strftime('%z')}"
        )
    except Exception:
        return f"변환 실패 ({mac_time})"


def format_phone_number(phone_str: str) -> str:
    """
    전화번호 포맷팅:
    - 숫자, '+', '-', 공백 외 문자가 있으면 원본 반환
    - '+82' 국제전화 코드는 '0' 접두로 변환
    - 11자리 '010' 시작 번호는 'xxx-xxxx-xxxx' 형식 반환
    """
    s = phone_str.strip()
    if not re.fullmatch(r"[+\d\s-]+", s):
        return phone_str

    if s.startswith("+82"):
        rest = s[3:].lstrip()
        s = rest if rest.startswith("0") else "0" + rest

    digits = re.sub(r"\D", "", s)
    if len(digits) == 11 and digits.startswith("010"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return s


# -----------------------------------------------------------------------------
# BackupPathHelper
# -----------------------------------------------------------------------------

class BackupPathHelper:
    """
    iOS 백업 폴더의 Manifest.db를 이용해 실제 파일 경로를 찾는 헬퍼 클래스.
    """

    def __init__(self, backup_path: str):
        self.backup_path = backup_path

    def get_file_path(self, relative_path: str) -> Optional[str]:
        """
        Manifest.db에서 relativePath 매핑을 조회해
        실제 백업 해시 경로를 반환. 실패 시 None.
        """
        manifest = os.path.join(self.backup_path, "Manifest.db")
        if not os.path.exists(manifest):
            return None

        try:
            with sqlite3.connect(manifest) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT fileID FROM Files WHERE relativePath = ?",
                    (relative_path,)
                )
                row = cur.fetchone()
            if row:
                fid = row[0]
                path = os.path.join(self.backup_path, fid[:2], fid)
                if os.path.exists(path):
                    return path
            return None
        except Exception:
            return None

    def find_sqlite_with_tables(self, tables: List[str]) -> Optional[str]:
        """
        백업 폴더를 스캔해 지정된 테이블이 존재하는 SQLite 파일 경로를 반환.
        """
        # TODO: 구현
        return None


# -----------------------------------------------------------------------------
# AddressBookEntry
# -----------------------------------------------------------------------------

class AddressBookEntry:
    """
    단일 주소록 항목(연락처) 정보를 저장하는 클래스.
    기본 속성과 다중값(전화번호, 이메일), 이미지 데이터를 포함.
    """

    def __init__(
        self,
        rowid: int,
        first_name: str = "",
        last_name: str = "",
        organization: str = "",
        note: str = "",
        **kwargs: Any,
    ):
        self.rowid = rowid
        self.first_name = first_name
        self.last_name = last_name
        self.organization = organization
        self.note = note

        # 선택 속성
        self.guid = kwargs.get("guid")
        self.creation_date = kwargs.get("CreationDate")
        self.modification_date = kwargs.get("ModificationDate")

        # 라벨별 다중값 저장
        self.values_by_label: Dict[str, List[str]] = {}
        # 이미지 바이트
        self.image: Optional[bytes] = None

    def add_value(self, label: Optional[str], value: str) -> None:
        """
        라벨별 다중값 속성(전화번호, 이메일 등)을 저장.
        """
        key = label or ""
        self.values_by_label.setdefault(key, []).append(value)

    def get_phone_number(self) -> str:
        """
        포맷된 전화번호들을 ', '로 연결하여 반환.
        """
        phone_keys = {"_$!<Mobile>!$_", "_$!<Home>!$_", "_$!<Work>!$_", "iPhone", "mobile", ""}
        numbers: List[str] = []
        for lbl, vals in self.values_by_label.items():
            if lbl in phone_keys:
                numbers += [format_phone_number(v) for v in vals]
        return ", ".join(numbers)

    def get_emails(self) -> str:
        """
        저장된 이메일 주소들을 ', '로 연결하여 반환.
        """
        email_keys = {"Home", "Work", "email", ""}
        emails: List[str] = []
        for lbl, vals in self.values_by_label.items():
            if lbl in email_keys:
                emails += vals
        return ", ".join(emails)

    def get_formatted_details(self) -> str:
        """
        HTML-like 문자열로 상세 정보를 반환.
        UI에서 <b>, <br> 태그로 렌더링 용이.
        """
        name = f"{self.last_name} {self.first_name}".strip()
        created = format_mac_time(self.creation_date) if self.creation_date else "N/A"
        modified = format_mac_time(self.modification_date) if self.modification_date else "N/A"
        return (
            f"<b>이름:</b> {name}<br>"
            f"<b>소속:</b> {self.organization}<br>"
            f"<b>전화번호:</b> {self.get_phone_number()}<br>"
            f"<b>이메일:</b> {self.get_emails()}<br>"
            f"<b>메모:</b> {self.note}<br><br>"
            f"<b>생성일:</b> {created} ({self.creation_date})<br>"
            f"<b>수정일:</b> {modified} ({self.modification_date})<br>"
            f"<b>GUID:</b> {self.guid}<br>"
        )


# -----------------------------------------------------------------------------
# AddressBookAnalyzer
# -----------------------------------------------------------------------------

class AddressBookAnalyzer:
    """
    iOS 백업에서 주소록 DB와 이미지 DB를 찾아
    주소록 항목과 프로필 사진을 함께 로드하는 분석기 클래스.
    """

    def __init__(self, backup_path: str):
        self.backup_path = backup_path
        self.helper = BackupPathHelper(backup_path)
        self.entries: List[AddressBookEntry] = []

    def _find_db(self, paths: List[str], tables: List[str]) -> Optional[str]:
        for p in paths:
            if path := self.helper.get_file_path(p):
                return path
        return self.helper.find_sqlite_with_tables(tables)

    def find_addressbook_db(self) -> Optional[str]:
        return self._find_db(
            [
                "Library/AddressBook/AddressBook.sqlitedb",
                "private/var/mobile/Library/AddressBook/AddressBook.sqlitedb",
            ],
            ["ABPerson", "ABMultiValue"],
        )

    def find_addressbook_images_db(self) -> Optional[str]:
        return self._find_db(
            [
                "Library/AddressBook/AddressBookImages.sqlitedb",
            ],
            ["ABFullSizeImage"],
        )

    def load_entries(self) -> Tuple[bool, str]:
        """
        주소록 항목과 다중값을 DB에서 로드합니다.
        반환: (성공여부, 메시지)
        """
        db = self.find_addressbook_db()
        if not db:
            return False, "AddressBook.sqlitedb를 찾을 수 없습니다."

        conn = sqlite3.connect(db)
        cur = conn.cursor()
        # ABPerson 동적 컬럼 조회
        cur.execute("PRAGMA table_info(ABPerson)")
        cols = [c[1] for c in cur.fetchall()]
        base = ["ROWID", "First", "Last", "Organization", "Note"]
        select = [c for c in base if c in cols] + [c for c in cols if c not in base]

        cur.execute(f"SELECT {','.join(select)} FROM ABPerson")
        rows = cur.fetchall()
        conn.close()

        self.entries = []
        for row in rows:
            data = dict(zip(select, row))
            entry = AddressBookEntry(
                rowid=data["ROWID"],
                first_name=data.get("First", ""),
                last_name=data.get("Last", ""),
                organization=data.get("Organization", ""),
                note=data.get("Note", ""),
                **{k: data.get(k) for k in select if k not in base},
            )
            self.entries.append(entry)

        # 다중값 로드
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(
            "SELECT MV.record_id, MV.value, LAB.value FROM ABMultiValue MV "
            "LEFT JOIN ABMultiValueLabel LAB ON MV.label = LAB.ROWID"
        )
        for rec_id, val, lbl in cur.fetchall():
            if ent := next((e for e in self.entries if e.rowid == rec_id), None):
                ent.add_value(lbl, val)
        conn.close()

        # 이미지 로드
        self._load_images()
        return True, f"주소록 {len(self.entries)}건 로드 완료"

    def _load_images(self) -> None:
        db = self.find_addressbook_images_db()
        if not db:
            return
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT record_id, data FROM ABFullSizeImage")
        img_map = {rid: data for rid, data in cur.fetchall()}
        conn.close()
        for e in self.entries:
            if data := img_map.get(e.rowid):
                e.image = data

    def get_entries(self) -> List[AddressBookEntry]:
        """로드된 주소록 항목 리스트를 반환."""
        return self.entries

    def search_entries(self, query: str = "") -> List[AddressBookEntry]:
        """
        query가 비어 있으면 전체 반환.
        이름·전화번호·소속 필드에 query 포함 항목 필터링.
        """
        if not query:
            return self.entries
        q = query.lower()
        filtered: List[AddressBookEntry] = []
        for e in self.entries:
            name = f"{e.last_name} {e.first_name}".strip().lower()
            phone = e.get_phone_number().lower().replace("-", "")
            org = e.organization.lower()
            if q in name or q in phone or q in org:
                filtered.append(e)
        return filtered