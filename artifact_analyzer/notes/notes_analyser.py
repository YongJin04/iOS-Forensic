
from __future__ import annotations

import os
import sqlite3
import zlib
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
    # 목록 / 상세에 공통으로 쓸 SELECT 구성
    BASE_SELECT = """
        SELECT
            ZSNIPPET                    AS "내용 미리보기",
            ZTITLE1                     AS "제목",
            ZACCOUNTNAMEFORACCOUNTLISTSORTING AS "계정명",
            ZCREATIONDATE3              AS "생성일(raw)",
            ZMODIFICATIONDATE1          AS "수정일(raw)",
            ZIDENTIFIER                 AS "식별자(노트 ID)",
            ZLASTOPENEDDATE             AS "마지막 열람(raw)",
            ZLASTATTRIBUTIONSVIEWEDDATE AS "속성 확인 시점(raw)",
            ZLASTACTIVITYRECENTUPDATESVIEWEDDATE AS "최근 업데이트 열람(raw)",
            ZLASTACTIVITYSUMMARYVIEWEDDATE AS "요약 열람 시점(raw)",
            ZLASTVIEWEDMODIFICATIONDATE AS "노트 보기 시점(raw)",
            ZPARENTMODIFICATIONDATE     AS "상위폴더 변경일(raw)"
        FROM ZICCLOUDSYNCINGOBJECT
    """

    # 목록용: ZSNIPPET 존재 필터 + 최신 수정일 순
    SUMMARY_SQL = (
        BASE_SELECT + " WHERE ZSNIPPET IS NOT NULL ORDER BY ZMODIFICATIONDATE1 DESC;"
    )

    # 상세용: 식별자 WHERE 절
    DETAIL_SQL = BASE_SELECT + " WHERE ZIDENTIFIER = ? LIMIT 1;"

    def __init__(self, backup_path: str):
        self.backup_path = backup_path
        self.default_relative = (
            "AppDomainGroup-group.com.apple.notes/NoteStore.sqlite"
        )
        self.conn: Optional[sqlite3.Connection] = None
        self.helper = BackupPathHelper(backup_path)

    # ─────────────────────────────────────────────────────────────
    # 내부 유틸
    # ─────────────────────────────────────────────────────────────
    def _ensure_connection(self) -> None:
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

    @staticmethod
    def _decode_snippet(blob: bytes | str | None) -> str:
        if blob is None:
            return ""
        if isinstance(blob, str):
            return blob
        if isinstance(blob, (bytes, bytearray)):
            try:
                return zlib.decompress(blob).decode("utf-8", "replace")
            except Exception:
                try:
                    return blob.decode("utf-8", "replace")
                except Exception:
                    return repr(blob)
        return str(blob)

    # ─────────────────────────────────────────────────────────────
    # DB 연결
    # ─────────────────────────────────────────────────────────────
    def connect_to_db(self) -> bool:
        relative = None
        try:
            manifest = os.path.join(self.backup_path, "Manifest.db")
            with sqlite3.connect(manifest) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT relativePath
                    FROM Files
                    WHERE domain LIKE 'AppDomainGroup-group.com.apple.notes%'
                      AND relativePath LIKE '%NoteStore.sqlite'
                    """
                )
                row = cur.fetchone()
                if row:
                    relative = row[0]
        except Exception as e:
            print(f"[!] Manifest 접근 오류: {e}")

        path = (
            self.helper.get_file_path_from_manifest(relative)
            if relative
            else os.path.join(self.backup_path, self.default_relative)
        )

        if path and os.path.exists(path):
            try:
                self.conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                self.conn.row_factory = sqlite3.Row
                print(f"[+] 노트 DB 연결 성공: {path}")
                return True
            except sqlite3.Error as e:
                print(f"[!] DB 연결 실패: {e}")
        return False

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    # ─────────────────────────────────────────────────────────────
    # 목록(요약) 추출
    # ─────────────────────────────────────────────────────────────
    def get_note_summaries(self) -> pd.DataFrame:
        """목록 표시용 DataFrame (GUI 필수 컬럼 매핑 포함)"""
        self._ensure_connection()

        cur = self.conn.cursor()
        cur.execute(self.SUMMARY_SQL)
        rows = cur.fetchall()

        records: List[Dict[str, str]] = []
        for r in rows:
            rec = dict(r)
            rec["내용 미리보기"] = self._decode_snippet(rec["내용 미리보기"])

            # 날짜 변환 + 원본 보존
            for raw in [c for c in rec if c.endswith("(raw)")]:
                pretty = raw.replace("(raw)", "").strip()
                rec[pretty] = self._apple_ts_to_kst(rec[raw])

            # GUI 호환 영문 컬럼
            rec["title"]           = rec.get("제목", "")
            rec["created_at_kst"]  = rec.get("생성일", "")
            rec["modified_at_kst"] = rec.get("수정일", "")
            rec["uuid"]            = rec.get("식별자(노트 ID)", "")
            rec["mime_type"]       = rec.get("mime_type", "")  # 추후 첨부파일 분석 시 채움

            records.append(rec)

        df = pd.DataFrame(records)

        # GUI 필수 컬럼 보장
        for col in ["title", "created_at_kst", "modified_at_kst", "uuid", "mime_type"]:
            if col not in df.columns:
                df[col] = ""

        return df

    # ─────────────────────────────────────────────────────────────
    # 상세 보기
    # ─────────────────────────────────────────────────────────────
    def get_note_detail(self, uuid: str) -> Dict[str, str]:
        """식별자(노트 ID)로 단일 노트 전체 필드 반환"""
        self._ensure_connection()

        cur = self.conn.cursor()
        cur.execute(self.DETAIL_SQL, (uuid,))
        row = cur.fetchone()
        if not row:
            raise KeyError(f"uuid '{uuid}' not found")

        rec = dict(row)
        rec["내용 미리보기"] = self._decode_snippet(rec["내용 미리보기"])

        # raw → KST 변환 추가
        for raw in [c for c in rec if c.endswith("(raw)")]:
            pretty = raw.replace("(raw)", "").strip()
            rec[pretty] = self._apple_ts_to_kst(rec[raw])

        # GUI 호환 필드도 함께
        rec["title"]           = rec.get("제목", "")
        rec["created_at_kst"]  = rec.get("생성일", "")
        rec["modified_at_kst"] = rec.get("수정일", "")

        return rec

    # GUI 호환 래퍼
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

    ios_backup = sys.argv[1]
    na = NotesAnalyser(ios_backup)

    # 1) 요약 목록
    df = na.get_note_summaries()
    print("=== 요약 목록 상위 5개 ===")
    print(df.head().to_string(index=False))

    # 2) 첫 번째 노트 상세 보기 예시
    if not df.empty:
        first_uuid = df.iloc[0]["uuid"]
        detail = na.get_note_detail(first_uuid)
        print("\n=== 상세 보기 ===")
        for k, v in detail.items():
            print(f"{k:25}: {v}")

    na.close()