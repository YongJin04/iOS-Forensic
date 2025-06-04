# line_analyzer.py

import os
import sqlite3
from datetime import datetime, timedelta  # Apple Absolute Time 변환을 위해 timedelta 사용
from typing import List, Dict, Optional


def format_time(ts: float) -> str:
    """
    Apple Absolute Time(2001-01-01 00:00:00 기준 초 단위, 
    밀리초 단위일 경우 자동으로 초 단위로 변환)으로 가정하고 
    사람이 읽을 수 있는 문자열(YYYY-MM-DD HH:MM:SS)로 변환.
    """
    try:
        # 밀리초 판별: 10^12 이상이면 밀리초
        if ts > 1e12:
            ts_sec = ts / 1000.0
        else:
            ts_sec = ts
        # Apple Absolute Time → Unix Epoch 변환
        # Apple 기준(2001-01-01 00:00:00)과 Unix 기준(1970-01-01 00:00:00) 사이의 초 차이
        APPLE_UNIX_OFFSET = 978307200  # seconds
        unix_ts = ts_sec + APPLE_UNIX_OFFSET
        dt = datetime.fromtimestamp(unix_ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


class ChatRow:
    __slots__ = ("chat_id", "last_send_raw", "last_send", "display_name")

    def __init__(self, chat_id: int, last_send: float):
        self.chat_id = chat_id
        self.last_send_raw = last_send
        self.last_send = format_time(last_send)
        self.display_name = ""  # 나중에 로드 단계에서 값을 채워넣습니다.


class LineAnalyzer:
    """
    LINE 메시지 DB에서 채팅방 목록(ZCHAT) 및 사용자(ZUSER) 정보를 읽어 들인 뒤,
    채팅방별 메시지(ZMESSAGE)를 파싱하여 반환하는 클래스.
    """
    # 사용자 데이터가 저장된 테이블 이름: ZUSER
    # 채팅방 데이터가 저장된 테이블 이름: ZCHAT
    # 메시지 데이터가 저장된 테이블 이름: ZMESSAGE

    def __init__(self, backup_root: str):
        """
        :param backup_root: 백업 디렉터리 경로. 예: "/path/to/backup"
                            LINE DB 파일은 backup_root/ce/ce21064ca3ffd3ee7a90147bf2d24b91ee9ba8c9 에 위치함.
        """
        self.backup_root = backup_root
        # ce 디렉터리 아래 고정된 파일명
        self.db_path = os.path.join(
            backup_root, "ce", "ce21064ca3ffd3ee7a90147bf2d24b91ee9ba8c9"
        )
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"LINE DB 파일을 찾을 수 없습니다: {self.db_path}")

        self.rows: List[ChatRow] = []
        self.users: Dict[int, str] = {}  # user_id -> user_name

    def _load_users(self) -> None:
        """
        ZUSER 테이블에서 Z_PK, ZNAME 컬럼을 읽어 self.users에 저장.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT Z_PK, ZNAME FROM ZUSER")
                for pk, name in cur.fetchall():
                    # ZNAME이 None이거나 빈 문자열일 수 있으므로 str() 처리
                    self.users[pk] = name or f"User_{pk}"
        except Exception:
            # 실패하더라도 빈 dict로 둡니다.
            pass

    def load(self) -> (bool, str):
        """
        ZCHAT 테이블의 Z_PK(Z채팅ID), ZLASTUPDATED(마지막 발신 시간) 컬럼을 읽어 ChatRow 객체 리스트를 생성.
        이후 ZUSER를 로드하여 self.users에 사용자 이름 매핑.
        각 ChatRow에 대해, 채팅방의 상대방 이름(display_name)을 ZMESSAGE에서 찾아 채워넣음.
        또한, Z_PK가 1인 채팅방은 self.rows에서 제외합니다.
        :return: (성공여부, 메시지)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                # ZCHAT: Z_PK(채팅방 고유 ID), ZLASTUPDATED(Apple Absolute Time)
                cur.execute("SELECT Z_PK, ZLASTUPDATED FROM ZCHAT")
                for pk, last_upd in cur.fetchall():
                    raw_ts = last_upd or 0
                    self.rows.append(ChatRow(pk, raw_ts))

            # ── Z_PK == 1인 채팅방은 아예 목록에서 제외 ───────────────────────────────
            self.rows = [r for r in self.rows if r.chat_id != 1]

            # 사용자 테이블 로드
            self._load_users()

            # ── 각 ChatRow에 대해 display_name(상대방 이름) 채워넣기 ─────────────────
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                for r in self.rows:
                    # 상대방(sender_id != 0) 중 가장 최근 메시지를 보낸 user_id를 가져옴
                    cur.execute(
                        """
                        SELECT ZSENDER 
                        FROM ZMESSAGE 
                        WHERE ZCHAT = ? AND ZSENDER IS NOT NULL AND ZSENDER != 0 
                        ORDER BY ZTIMESTAMP DESC 
                        LIMIT 1
                        """,
                        (r.chat_id,),
                    )
                    res = cur.fetchone()
                    if res:
                        uid = res[0] or 0
                        r.display_name = self.users.get(uid, f"User_{uid}")
                    else:
                        # 모든 메시지를 내가 보냈거나 메시지 없음 → 대체 텍스트 지정
                        r.display_name = "Unknown"

            # 마지막 발신 시간 내림차순 정렬
            self.rows.sort(key=lambda r: r.last_send_raw, reverse=True)
            return True, f"{len(self.rows)}개의 채팅방을 로드했습니다."
        except Exception as e:
            return False, f"DB 로딩 오류: {e}"

    def get_messages(self, chat_id: int) -> List[Dict]:
        """
        특정 채팅방(chat_id)에 속한 메시지를 ZMESSAGE 테이블에서 읽어 사전 리스트로 반환.
        반환되는 dict 구조:
            {
                "message_id": ZID,
                "message": ZTEXT or "",
                "send_time": 변환된 타임스트링(format_time),
                "sender_id": ZSENDER(None이면 0으로 처리),
                "sender_name": self.users.get(ZSENDER) or "Me" (ZSENDER이 None/0일 경우)
            }
        :param chat_id: ZCHAT의 Z_PK 값
        """
        out: List[Dict] = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                # ZMESSAGE: ZCHAT 컬럼이 chat_id인 레코드 조회, ZTIMESTAMP(발신 시각) 기준 정렬
                cur.execute(
                    """
                    SELECT ZTEXT, ZID, ZTIMESTAMP, ZSENDER, ZCHAT
                    FROM ZMESSAGE
                    WHERE ZCHAT = ?
                    ORDER BY ZTIMESTAMP ASC
                    """,
                    (chat_id,),
                )
                for text, zid, zts, zsender, zchat in cur.fetchall():
                    raw_ts = zts or 0
                    send_time_str = format_time(raw_ts)
                    # ZSENDER이 None 또는 0이면 사용자가 보낸 메시지로 간주
                    sender_id: int = zsender or 0
                    if sender_id == 0:
                        sender_name = "Me"
                    else:
                        sender_name = self.users.get(sender_id, f"User_{sender_id}")
                    out.append(
                        {
                            "message_id": zid,
                            "message": text or "",
                            "send_time": send_time_str,
                            "sender_id": sender_id,
                            "sender_name": sender_name,
                            "chat_id": zchat,
                        }
                    )
        except Exception:
            # 실패 시 빈 리스트 반환
            pass
        return out

    def search(self, keyword: str) -> List[ChatRow]:
        """
        채팅방 리스트(self.rows)에서 채팅 ID 또는 문자열이 keyword에 포함된 행만 필터하여 반환.
        (ChatRow.chat_id 또는 ChatRow.last_send 또는 ChatRow.display_name 포함 여부로 검색)
        """
        k = keyword.lower().strip()
        return [
            r
            for r in self.rows
            if k in str(r.chat_id)
            or k in r.last_send.lower()
            or k in r.display_name.lower()
        ]
