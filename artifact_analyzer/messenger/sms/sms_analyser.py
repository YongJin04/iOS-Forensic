import os, re, sqlite3
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional


MAC_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
PHONE_RE = re.compile(r"\d+")

def digits_only(s: str) -> str:
    return "".join(PHONE_RE.findall(s or ""))

def _to_seconds(val: float) -> float:
    """Apple Absolute Time 단위를 초로 환산(나노·마이크로·밀리 자동 판별)"""
    if val > 1e14:          # 나노초
        return val / 1_000_000_000
    if val > 1e11:          # 마이크로초
        return val / 1_000_000
    if val > 1e9:           # 밀리초
        return val / 1_000
    return val              # 이미 초

def ts_to_kst(ts: float) -> str:
    try:
        sec = _to_seconds(ts)
        dt = MAC_EPOCH + timedelta(seconds=sec)
        return dt.astimezone(timezone(timedelta(hours=9))).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    except Exception:
        return str(ts)


class ChatRow:
    __slots__ = (
        "chat_id",
        "identifier",
        "last_read_raw",
        "last_read",
        "last_msg_raw",
        "name",
    )

    def __init__(
        self, chat_id: int, identifier: str, last_read: float, last_msg: float
    ):
        self.chat_id = chat_id
        self.identifier = identifier or ""
        self.last_read_raw = last_read
        self.last_read = ts_to_kst(last_read)
        self.last_msg_raw = last_msg
        self.name = ""  # AddressBook 보완 후 채워짐


class IMessageAnalyzer:
    CHAT_DB_REL = os.path.join("3d", "3d0d7e5fb2ce288813306e4d4636395e047a3d28")
    AB_DB_REL = os.path.join("31", "31bb7ba8914766d4ba40d6dfb6113c8b614be442")

    def __init__(self, backup_root: str):
        self.backup_root = backup_root
        self.chat_db = os.path.join(backup_root, self.CHAT_DB_REL)
        self.ab_db = os.path.join(backup_root, self.AB_DB_REL)
        if not os.path.exists(self.chat_db):
            raise FileNotFoundError("chat.db not found")
        self.rows: List[ChatRow] = []

    # ─────────── 채팅 목록 로드 ───────────
    def load(self) -> Tuple[bool, str]:
        try:
            with sqlite3.connect(self.chat_db) as conn:
                cur = conn.cursor()

                # 각 chat_id 의 최신 메시지 시간 맵
                cur.execute(
                    """
                    SELECT chat_id, MAX(m.date) AS max_date
                    FROM chat_message_join cmj
                    JOIN message m ON m.ROWID = cmj.message_id
                    GROUP BY chat_id
                    """
                )
                latest = {cid: ts for cid, ts in cur.fetchall()}

                # chat 테이블
                cur.execute(
                    """
                    SELECT ROWID, chat_identifier, last_read_message_timestamp
                    FROM chat
                    """
                )
                for cid, ident, last_read in cur.fetchall():
                    self.rows.append(
                        ChatRow(
                            cid,
                            ident or "",
                            last_read or 0,
                            latest.get(cid, 0),
                        )
                    )
            # 이름 보완
            self._patch_names()
            # LastRead 내림차순
            self.rows.sort(key=lambda r: r.last_read_raw, reverse=True)
            return True, f"{len(self.rows)} chats"
        except Exception as e:
            return False, f"DB 오류: {e}"

    # ─────────── 전화번호 → 이름 보완 ───────────
    def _patch_names(self):
        if not os.path.exists(self.ab_db):
            return
        try:
            with sqlite3.connect(self.ab_db) as conn:
                cur = conn.cursor()
                for r in self.rows:
                    digits = digits_only(r.identifier)
                    if not digits:
                        continue
                    cur.execute(
                        "SELECT docid FROM ABPersonFullTextSearch_content WHERE c16Phone LIKE ? LIMIT 1",
                        (f"%{digits}%",),
                    )
                    row = cur.fetchone()
                    if not row:
                        continue
                    cur.execute(
                        "SELECT First, Last FROM ABPerson WHERE ROWID = ? LIMIT 1",
                        (row[0],),
                    )
                    p = cur.fetchone()
                    if p:
                        r.name = " ".join(x for x in (p[1], p[0]) if x).strip()
        except Exception:
            pass

    # ─────────── 채팅별 메시지 ───────────
    def get_messages(self, chat_id: int) -> List[Dict]:
        """
        반환: [{datetime, direction('발신'|'수신'|'?'), body(str), attachment(str)}...]
        """
        out = []
        with sqlite3.connect(self.chat_db) as conn:
            cur = conn.cursor()

            # chat_message_join → message_id, date
            cur.execute(
                """
                SELECT m_id, m_date FROM (
                  SELECT message_id AS m_id, message_date AS m_date
                  FROM chat_message_join WHERE chat_id = ?
                )
                ORDER BY m_date
                """,
                (chat_id,),
            )
            id_ts_pairs = cur.fetchall()

            for mid, ts in id_ts_pairs:
                # 1) message 테이블 존재?
                cur.execute(
                    "SELECT text, is_from_me, guid FROM message WHERE ROWID = ?",
                    (mid,),
                )
                m = cur.fetchone()
                if m:
                    text, from_me, guid = m
                    body = text or ""
                    # 첨부가 필요하면
                    if not body:
                        cur.execute(
                            """
                            SELECT attachment.filename
                            FROM attachment
                            JOIN message_attachment_join maj ON attachment.ROWID = maj.attachment_id
                            WHERE maj.message_id = ? LIMIT 1
                            """,
                            (mid,),
                        )
                        a = cur.fetchone()
                        attach = a[0] if a else ""
                    else:
                        attach = ""
                    out.append(
                        {
                            "datetime": ts_to_kst(ts),
                            "direction": "발신" if from_me else "수신",
                            "body": body,
                            "attachment": attach,
                        }
                    )
                    continue  # 다음 id

                # 2) message 가 없다면 attachment ROWID 매칭
                cur.execute(
                    "SELECT filename FROM attachment WHERE ROWID = ?",
                    (mid,),
                )
                a = cur.fetchone()
                if a:
                    out.append(
                        {
                            "datetime": ts_to_kst(ts),
                            "direction": "수신",
                            "body": "",
                            "attachment": a[0],
                        }
                    )
        return out

    # ─────────── 검색 ───────────
    def search(self, kw: str) -> List[ChatRow]:
        k = kw.lower()
        return [
            r
            for r in self.rows
            if k in str(r.chat_id)
            or k in r.identifier.lower()
            or k in r.name.lower()
            or k in r.last_read.lower()
        ]
