"""
contact_content.py
- 31/31bb7ba8914766d4ba40d6dfb6113c8b614be442 (AddressBook.sqlitedb) 에서
  연락처 기본 정보 + 휴대폰(010…) 한 개를 파싱
"""

import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple


# ──────────────────────────────
# 유틸
# ──────────────────────────────
MAC_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


def mac_absolute_to_str(sec: float) -> str:
    """Mac epoch(2001-01-01) 기준 초 → YYYY-MM-DD HH:MM:SS"""
    try:
        kst = MAC_EPOCH + timedelta(seconds=sec)
        kst = kst.astimezone(timezone(timedelta(hours=9)))
        return kst.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


_PHONE_010_RE = re.compile(r"(?:\+?82)?0?1[016789]\d{7,8}")


def pick_cell_010(phone_blob: str) -> str:
    """c16Phone 문자열에서 010… 형태 하나만 추출"""
    for m in _PHONE_010_RE.finditer(phone_blob):
        digits = re.sub(r"\D", "", m.group())
        if len(digits) == 11 and digits.startswith("010"):
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return ""


# ──────────────────────────────
# DTO
# ──────────────────────────────
class ContactRow:
    def __init__(
        self,
        rowid: int,
        first: str,
        last: str,
        org: str,
        c_date: float,
        m_date: float,
        phone: str,
    ):
        self.rowid = rowid
        self.first = first
        self.last = last
        self.org = org
        self.created_raw = c_date
        self.modified_raw = m_date
        self.phone = phone

    # 편의 문자열
    @property
    def full_name(self) -> str:
        return f"{self.last} {self.first}".strip()

    @property
    def created(self) -> str:
        return mac_absolute_to_str(self.created_raw)

    @property
    def modified(self) -> str:
        return mac_absolute_to_str(self.modified_raw)


# ──────────────────────────────
# Analyzer
# ──────────────────────────────
class ContactContentAnalyzer:
    """AddressBook.sqlitedb 파서"""

    DB_REL = os.path.join(
        "31", "31bb7ba8914766d4ba40d6dfb6113c8b614be442"
    )

    def __init__(self, backup_path: str):
        self.db_path = os.path.join(backup_path, self.DB_REL)
        self.contacts: List[ContactRow] = []

    # ―― 메인 로드 ――
    def load_contacts(self) -> Tuple[bool, str]:
        if not os.path.exists(self.db_path):
            return False, f"DB 파일이 없습니다: {self.db_path}"

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # ABPerson 기본 정보
            cur.execute(
                """
                SELECT ROWID, First, Last, Organization,
                       CreationDate, ModificationDate
                FROM ABPerson
                """
            )
            base_rows = cur.fetchall()

            # 전화번호 맵 만들기 (docid == ROWID)
            cur.execute(
                """
                SELECT docid, c16Phone
                FROM ABPersonFullTextSearch_content
                """
            )
            phone_map = {doc: pick_cell_010(blob or "") for doc, blob in cur.fetchall()}

            conn.close()

            self.contacts = [
                ContactRow(
                    r[0],
                    r[1] or "",
                    r[2] or "",
                    r[3] or "",
                    r[4] or 0.0,
                    r[5] or 0.0,
                    phone_map.get(r[0], ""),
                )
                for r in base_rows
            ]
            return True, f"{len(self.contacts)}건 로드"
        except Exception as e:
            return False, f"DB 읽기 오류: {e}"

    # ―― 검색 ――
    def search(self, kw: str = "") -> List[ContactRow]:
        if not kw:
            return self.contacts
        k = kw.lower()
        return [
            c
            for c in self.contacts
            if k in str(c.rowid)
            or k in c.full_name.lower()
            or k in c.org.lower()
            or k in c.phone.replace("-", "")
        ]
