import os
import sqlite3
import base64
import json
from datetime import datetime
from typing import List, Optional, Tuple

MAC_EPOCH_OFFSET = 978307200  # 2001-01-01 00:00:00 UTC


# ---------- 공통 포맷터 ---------- #
def format_korean_datetime(zdate: float) -> str:
    ts = zdate + MAC_EPOCH_OFFSET
    dt = datetime.fromtimestamp(ts)
    weekday = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]
    ap = "오전" if dt.hour < 12 else "오후"
    h12 = dt.hour if dt.hour in (0, 12) else dt.hour % 12
    return f"{dt.year}-{dt.month:02d}-{dt.day:02d}({weekday}) {ap} {h12}:{dt.minute:02d}:{dt.second:02d}"


def format_duration(sec: float) -> str:
    if sec < 60:
        return f"{sec:.1f}초"
    m = int(sec) // 60
    r = sec - m * 60
    return f"{m}분" if r < 0.05 else f"{m}분 {r:.1f}초"


# ---------- DTO ---------- #
class CallRecord:
    """단일 통화 기록"""

    def __init__(
        self,
        z_pk: int,
        ztype: int,
        zvalue: str,
        zname: str,
        zdate: float,
        zduration: float,
        zaddress_raw,
        service_provider: Optional[str],
        z_opt: int,
    ):
        self.z_pk = z_pk                # 내부 식별용
        self.ztype = ztype
        self.zvalue = zvalue or ""
        self.phone_number = self._extract_display_name_or_value(self.zvalue)
        self.zname = zname or ""
        self.zdate = zdate or 0.0
        self.zduration = float(zduration or 0)
        self.zaddress_raw = zaddress_raw
        self.caller_name = self._try_base64(zaddress_raw)

        # Service: 마지막 '.' 뒤 토큰
        self.service_raw = service_provider or ""
        self.service = self.service_raw.split(".")[-1] if self.service_raw else ""

        self.z_opt = z_opt  # 2=Incoming, 1=Outgoing

    # ---- 계산 필드 ---- #
    @property
    def direction(self) -> str:
        return "Incoming" if self.z_opt == 2 else ("Outgoing" if self.z_opt == 1 else "")

    @property
    def date_str(self) -> str:
        return format_korean_datetime(self.zdate)

    @property
    def duration_str(self) -> str:
        return format_duration(self.zduration)

    # ---- 내부 유틸 ---- #
    @staticmethod
    def _try_base64(data) -> str:
        if not data:
            return ""
        try:
            raw = data if isinstance(data, (bytes, bytearray)) else str(data).encode()
            return base64.b64decode(raw, validate=True).decode("utf-8", "ignore")
        except Exception:
            return str(data)

    def _extract_display_name_or_value(self, raw_val: str) -> str:
        decoded = self._try_base64(raw_val)
        try:
            obj = json.loads(decoded)
            if isinstance(obj, dict) and "threadDisplayName" in obj:
                return obj["threadDisplayName"]
        except Exception:
            pass
        return decoded or str(raw_val)


# ---------- Analyzer ---------- #
class CallHistoryAnalyzer:
    """iOS 통화 기록 파서"""

    def __init__(self, backup_path: str):
        self.backup_path = backup_path
        self.db_path: Optional[str] = None
        self.call_records: List[CallRecord] = []

    # DB 경로
    def _resolve_db_path(self) -> Tuple[bool, str]:
        fixed = os.path.join(
            self.backup_path, "5a", "5a4935c78a5255723f707230a451d79c540d2741"
        )
        if os.path.exists(fixed):
            self.db_path = fixed
            return True, fixed
        return False, f"통화 DB 없음: {fixed}"

    # 연락처 DB 경로 (Name 보완용)
    def _resolve_contacts_path(self) -> Optional[str]:
        path = os.path.join(
            self.backup_path, "31", "31bb7ba8914766d4ba40d6dfb6113c8b614be442"
        )
        return path if os.path.exists(path) else None

    # 메인 로드
    def load_call_records(self) -> Tuple[bool, str]:
        ok, msg = self._resolve_db_path()
        if not ok:
            return False, msg

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    h.Z_PK,             -- 0
                    h.ZTYPE,            -- 1
                    h.ZVALUE,           -- 2
                    c.ZNAME,            -- 3
                    c.ZDATE,            -- 4
                    c.ZDURATION,        -- 5
                    c.ZADDRESS,         -- 6
                    c.ZSERVICE_PROVIDER,-- 7
                    c.Z_OPT             -- 8 (2=In,1=Out)
                FROM ZHANDLE h
                INNER JOIN ZCALLRECORD c ON c.Z_PK = h.Z_PK
                ORDER BY c.ZDATE DESC;
                """
            )
            self.call_records = [CallRecord(*row) for row in cur.fetchall()]
            conn.close()

            self._patch_missing_names()
            return True, f"{len(self.call_records)}개의 기록"
        except Exception as e:
            return False, f"통화 DB 오류: {e}"

    # 이름 보완
    def _patch_missing_names(self):
        contacts_db = self._resolve_contacts_path()
        if not contacts_db:
            return
        try:
            conn = sqlite3.connect(contacts_db)
            cur = conn.cursor()
            for rec in self.call_records:
                if rec.zname:
                    continue
                digits = self._digits_only(rec.phone_number or rec.zvalue)
                if not digits:
                    continue
                cur.execute(
                    """
                    SELECT docid
                    FROM ABPersonFullTextSearch_content
                    WHERE c16Phone LIKE ?
                    LIMIT 1;
                    """,
                    (f"%{digits}%",),
                )
                row = cur.fetchone()
                if not row:
                    continue
                docid = row[0]
                cur.execute(
                    "SELECT First, Last FROM ABPerson WHERE ROWID = ? LIMIT 1;",
                    (docid,),
                )
                person = cur.fetchone()
                if not person:
                    continue
                first, last = person
                patched = " ".join(p for p in (last, first) if p).strip()
                if patched:
                    rec.zname = patched
            conn.close()
        except Exception:
            pass  # 무시

    @staticmethod
    def _digits_only(text: str) -> str:
        return "".join(ch for ch in text if ch.isdigit())

    # 검색
    def search(self, kw: str = "") -> List[CallRecord]:
        if not kw:
            return self.call_records
        k = kw.lower()
        return [
            r
            for r in self.call_records
            if k in r.phone_number.lower()
            or k in r.zvalue.lower()
            or k in r.zname.lower()
            or k in r.date_str.lower()
            or k in r.duration_str.lower()
            or k in r.service.lower()
            or k in r.direction.lower()
        ]
