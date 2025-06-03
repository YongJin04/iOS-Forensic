from __future__ import annotations

import os
import sqlite3
import zlib
import gzip
import base64
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

import pandas as pd


# ────────────────────────────────────────────────────────────────────────────
# Manifest 경로 매핑 헬퍼
# ────────────────────────────────────────────────────────────────────────────
class BackupPathHelper:
    def __init__(self, backup_path: str):
        self.backup_path = backup_path

    def get_file_path_from_manifest(self, relative_path: str) -> Optional[str]:
        manifest = os.path.join(self.backup_path, "Manifest.db")
        if not os.path.exists(manifest):
            print(f"[!] Manifest.db 없음: {manifest}")
            return None

        try:
            with sqlite3.connect(manifest) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT fileID FROM Files WHERE relativePath = ?",
                    (relative_path,),
                )
                row = cur.fetchone()
            if not row:
                print(f"[!] Manifest에 상대 경로 없음: {relative_path}")
                return None

            file_id = row[0]
            path = os.path.join(self.backup_path, file_id[:2], file_id)
            return path if os.path.exists(path) else None
        except Exception as e:
            print(f"[!] Manifest 검색 오류: {e}")
            return None


# ────────────────────────────────────────────────────────────────────────────
# 노트 분석기
# ────────────────────────────────────────────────────────────────────────────
class NotesAnalyser:
    SUMMARY_SQL = """
        SELECT
            main.ZSNIPPET                    AS "내용 미리보기",
            main.ZTITLE1                     AS "제목",
            main.ZCREATIONDATE3              AS "생성일(raw)",
            main.ZMODIFICATIONDATE1          AS "수정일(raw)",
            main.ZIDENTIFIER                 AS "식별자(노트 ID)"
        FROM ZICCLOUDSYNCINGOBJECT AS main
        WHERE main.ZSNIPPET IS NOT NULL
        ORDER BY main.ZMODIFICATIONDATE1 DESC;
    """

    DETAIL_SQL = """
        SELECT
            main.ZSNIPPET                    AS "내용 미리보기",
            main.ZTITLE1                     AS "제목",
            main.ZCREATIONDATE3              AS "생성일(raw)",
            main.ZMODIFICATIONDATE1          AS "수정일(raw)",
            main.ZIDENTIFIER                 AS "식별자(노트 ID)",
            data.*
        FROM ZICCLOUDSYNCINGOBJECT AS main
        LEFT JOIN ZICNOTEDATA      AS data ON data.ZNOTE = main.Z_PK
        WHERE main.ZIDENTIFIER = ?
        LIMIT 1;
    """

    def __init__(self, backup_path: str):
        self.backup_path = backup_path
        self.conn: Optional[sqlite3.Connection] = None
        self.helper = BackupPathHelper(backup_path)
        self.default_relative = "AppDomainGroup-group.com.apple.notes/NoteStore.sqlite"

    # ─────────────────────────────────────────────
    # 내부 유틸
    # ─────────────────────────────────────────────
    def _ensure_connection(self):
        if self.conn is None and not self.connect_to_db():
            raise RuntimeError("노트 데이터베이스에 연결할 수 없습니다.")

    @staticmethod
    def _apple_ts_to_kst(ts: float | None) -> str:
        if ts is None or pd.isna(ts):
            return ""
        base = datetime(2001, 1, 1, tzinfo=timezone.utc)
        return (base + timedelta(seconds=ts)).astimezone(
            timezone(timedelta(hours=9))
        ).strftime("%Y-%m-%d %H:%M:%S")

    # ───────────── 텍스트 정규화 + 노이즈 컷 ─────────────
    @staticmethod
    def _sanitize_text(s: str) -> str:
        """
        1) 유니코드 치환 문자·NULL·비출력 제어문자 제거  
        2) **3줄 연속 ‘읽을거리 비율’이 0.3 미만이면 그 지점에서 잘라낸다**
           → 압축 바이트가 텍스트로 잘못 변환돼 생기는 잡음 제거
        """
        allowed_ws = {"\n", "\r", "\t"}
        printable = "".join(
            ch for ch in s.replace("\uFFFD", "")
            if (ch in allowed_ws) or ch.isprintable()
        )

        # --- 노이즈 라인 트리밍 ----------------------------------
        def is_noise(line: str) -> bool:
            """알파벳·숫자·한글이 차지하는 비율이 0.3 미만이면 noise"""
            if not line.strip():
                return False  # 빈 줄은 허용
            letters = sum(ch.isalnum() or ('\uAC00' <= ch <= '\uD7A3') for ch in line)
            return (letters / len(line)) < 0.3

        kept_lines: list[str] = []
        noise_streak = 0
        for ln in printable.splitlines():
            if is_noise(ln):
                noise_streak += 1
            else:
                noise_streak = 0
            if noise_streak >= 3:
                break  # 그 지점부터 이후는 버린다
            kept_lines.append(ln)
        return "\n".join(kept_lines).rstrip()

    # ───────────── 바이트 → 텍스트 복원 ─────────────
    @classmethod
    def _decode_blob(cls, blob):
        """
        bytes → (1) zlib  (2) gzip  (3) base64-zlib/gzip  (4) UTF-8
        str   → 그대로
        마지막에 _sanitize_text() 호출 → **잡음 제거**
        """
        if blob is None:
            return ""

        # 문자열
        if isinstance(blob, str):
            return cls._sanitize_text(blob)

        # 바이트
        if isinstance(blob, (bytes, bytearray)):
            raw: bytes = bytes(blob)

            # 1) zlib
            try:
                return cls._sanitize_text(
                    zlib.decompress(raw).decode("utf-8", "replace")
                )
            except Exception:
                pass

            # 2) gzip (헤더 0x1F 0x8B)
            if raw[:2] == b"\x1f\x8b":
                try:
                    return cls._sanitize_text(
                        gzip.decompress(raw).decode("utf-8", "replace")
                    )
                except Exception:
                    pass

            # 3) base64 → zlib/gzip
            try:
                b64 = base64.b64decode(raw, validate=True)
                try:
                    return cls._sanitize_text(
                        zlib.decompress(b64).decode("utf-8", "replace")
                    )
                except Exception:
                    if b64[:2] == b"\x1f\x8b":
                        return cls._sanitize_text(
                            gzip.decompress(b64).decode("utf-8", "replace")
                        )
            except Exception:
                pass

            # 4) 그냥 UTF-8
            try:
                return cls._sanitize_text(raw.decode("utf-8", "replace"))
            except Exception:
                return ""

        # 그 외
        return cls._sanitize_text(str(blob))

    # ─────────────────────────────────────────────
    # DB 연결
    # ─────────────────────────────────────────────
    def connect_to_db(self) -> bool:
        relative = None
        try:
            manifest = os.path.join(self.backup_path, "Manifest.db")
            with sqlite3.connect(manifest) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT relativePath
                    FROM Files
                    WHERE domain LIKE 'AppDomainGroup-group.com.apple.notes%'
                      AND relativePath LIKE '%NoteStore.sqlite'
                """)
                row = cur.fetchone()
                if row:
                    relative = row[0]
        except Exception as e:
            print(f"[!] Manifest 접근 오류: {e}")

        db_path = (
            self.helper.get_file_path_from_manifest(relative)
            if relative else
            os.path.join(self.backup_path, self.default_relative)
        )
        if db_path and os.path.exists(db_path):
            try:
                self.conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                self.conn.row_factory = sqlite3.Row
                print(f"[+] 노트 DB 연결 성공: {db_path}")
                return True
            except sqlite3.Error as e:
                print(f"[!] DB 연결 실패: {e}")
        return False

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ─────────────────────────────────────────────
    # 목록 (요약)
    # ─────────────────────────────────────────────
    def get_note_summaries(self) -> pd.DataFrame:
        self._ensure_connection()
        cur = self.conn.cursor()
        cur.execute(self.SUMMARY_SQL)
        rows = cur.fetchall()

        recs: List[Dict[str, str]] = []
        for r in rows:
            d = dict(r)
            d["내용 미리보기"] = self._decode_blob(d["내용 미리보기"])
            # 타임스탬프 변환
            for raw in [c for c in d if c.endswith("(raw)")]:
                pretty = raw.replace("(raw)", "").strip()
                d[pretty] = self._apple_ts_to_kst(d[raw])
            # GUI용 필드
            d["title"]           = d.get("제목", "")
            d["created_at_kst"]  = d.get("생성일", "")
            d["modified_at_kst"] = d.get("수정일", "")
            d["uuid"]            = d.get("식별자(노트 ID)", "")
            recs.append(d)

        df = pd.DataFrame(recs)
        for col in ["title", "created_at_kst", "modified_at_kst", "uuid"]:
            if col not in df.columns:
                df[col] = ""
        return df

    # ─────────────────────────────────────────────
    # 상세 (본문 포함)
    # ─────────────────────────────────────────────
    def get_note_detail(self, uuid: str) -> Dict[str, str]:
        self._ensure_connection()
        cur = self.conn.cursor()
        cur.execute(self.DETAIL_SQL, (uuid,))
        row = cur.fetchone()
        if not row:
            raise KeyError(f"uuid '{uuid}' not found")

        d = dict(row)

        # 미리보기
        d["내용 미리보기"] = self._decode_blob(d.get("내용 미리보기"))

        # 본문 후보
        candidate_cols = [
            "ZMARKUPSTRING",
            "ZHTMLSTRING1",
            "ZHTMLSTRING",
            "ZDATA",
        ]
        body = ""
        for col in candidate_cols:
            if col in d and d[col]:
                body = self._decode_blob(d[col])
                if body:
                    break
        d["content"] = body or d["내용 미리보기"]

        # 타임스탬프
        for raw in [c for c in d if c.endswith("(raw)")]:
            pretty = raw.replace("(raw)", "").strip()
            d[pretty] = self._apple_ts_to_kst(d[raw])

        # 편의 필드
        d["title"]           = d.get("제목", "")
        d["created_at_kst"]  = d.get("생성일", "")
        d["modified_at_kst"] = d.get("수정일", "")
        return d

    # GUI 래퍼
    def get_all_notes(self) -> pd.DataFrame:
        return self.get_note_summaries()


# ────────────────────────────────────────────────────────────────────────────
# CLI 테스트
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("사용법: python notes_analyser.py /path/to/iOS_Backup")
        sys.exit(1)
    backup = sys.argv[1]
    na = NotesAnalyser(backup)

    df = na.get_note_summaries()
    print("=== 요약 상위 5개 ===\n", df.head().to_string(index=False))

    if not df.empty:
        detail = na.get_note_detail(df.iloc[0]["uuid"])
        print("\n=== 상세 본문 (앞 300자) ===")
        print(detail["content"][:300])

    na.close()
