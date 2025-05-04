#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iOS 통화 기록 분석 모듈
 - iOS 백업에서 CallHistory.storedata 파일을 찾아 분석하는 기능 제공
 - 통화 기록 조회, 메타데이터 분석, 삭제된 레코드 탐지 기능 포함
"""

import os
import sqlite3
from datetime import datetime
import pandas as pd
from typing import Optional, List, Dict, Tuple, Union, Any


class BackupPathHelper:
    """
    iOS 백업 내부의 파일을 Manifest.db를 사용하여 찾는 도우미 클래스
    """

    def __init__(self, backup_path: str):
        self.backup_path = backup_path

    def get_file_path_from_manifest(self, relative_path: str) -> Optional[str]:
        """
        Manifest.db에서 참조된 파일의 절대 경로를 반환하거나 
        찾을 수 없는 경우 None을 반환
        """
        manifest_path = os.path.join(self.backup_path, "Manifest.db")
        if not os.path.exists(manifest_path):
            print(f"[Error] Manifest.db를 찾을 수 없습니다: {manifest_path}")
            return None

        try:
            with sqlite3.connect(manifest_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT fileID FROM Files WHERE relativePath = ?", (relative_path,)
                )
                result = cursor.fetchone()

            if result:
                file_hash = result[0]
                file_path = os.path.join(self.backup_path, file_hash[:2], file_hash)
                if os.path.exists(file_path):
                    return file_path
                print(
                    f"[Warning] 해시가 Manifest.db에 있지만 파일이 디스크에 없습니다: {file_path}"
                )
            else:
                print(f"[Warning] {relative_path}를 Manifest.db에서 찾을 수 없습니다")
        except Exception as e:
            print(f"[Error] Manifest.db 쿼리 실패: {e}")
        return None


class CallHistoryAnalyzer:
    """
    iOS 백업에서 추출한 통화 기록 데이터베이스를 분석하고
    포렌식 처리를 위한 도우미 메서드를 제공
    """

    # Mac/iOS epoch (2001-01-01)와 Unix epoch (1970-01-01)의 차이는 978307200초
    IOS_EPOCH = 978307200

    def __init__(self, backup_path: str):
        """
        CallHistoryAnalyzer 초기화
        
        Args:
            backup_path (str): iOS 백업 디렉토리 경로
        """
        self.backup_path = backup_path
        self.default_callhistory_db_path = os.path.join(
            backup_path, "Library", "CallHistoryDB", "CallHistory.storedata"
        )
        self.conn: Optional[sqlite3.Connection] = None
        self.path_helper = BackupPathHelper(backup_path)

    # ---------------------------------------------------------------------
    # 연결 관련 도우미 메서드
    # ---------------------------------------------------------------------
    def connect_to_db(self) -> bool:
        """
        CallHistory.storedata에 읽기 전용 연결을 엽니다.
        
        성공 시 True를, 그렇지 않으면 False를 반환합니다.
        """
        relative_path = "Library/CallHistoryDB/CallHistory.storedata"
        callhistory_db_path = self.path_helper.get_file_path_from_manifest(relative_path)
        
        if not callhistory_db_path:
            print("[Info] Manifest 조회 실패. 기본 경로로 대체합니다.")
            callhistory_db_path = self.default_callhistory_db_path

        if not os.path.exists(callhistory_db_path):
            print("[Error] 통화 기록 데이터베이스 파일을 찾을 수 없습니다.")
            return False

        try:
            # 실수로 변경되는 것을 방지하기 위해 읽기 전용으로 열기
            self.conn = sqlite3.connect(f"file:{callhistory_db_path}?mode=ro", uri=True)
            self.conn.row_factory = sqlite3.Row
            return True
        except sqlite3.Error as e:
            print(f"[Error] 데이터베이스에 연결할 수 없습니다: {e}")
            return False

    def close_connection(self) -> None:
        """데이터베이스 연결을 종료합니다."""
        if self.conn:
            self.conn.close()
            self.conn = None

    # ---------------------------------------------------------------------
    # 내부 도우미 메서드
    # ---------------------------------------------------------------------
    def _convert_date(self, raw_value) -> Optional[datetime]:
        """CoreData 타임스탬프를 datetime으로 변환(현지 시간)"""
        try:
            raw_value = float(raw_value)
        except (ValueError, TypeError):
            return None

        try:
            return datetime.fromtimestamp(raw_value + self.IOS_EPOCH)
        except Exception:
            return None

    def _format_korean_date(self, dt: datetime) -> str:
        """
        datetime 객체를 한국어 날짜/시간 형식으로 변환합니다.
        
        Args:
            dt (datetime): 변환할 datetime 객체
            
        Returns:
            str: "YYYY년 M월 D일 요일 오전/오후 h:mm:ss GMT+09:00" 형식의 날짜/시간
        """
        if not dt:
            return "날짜 없음"
            
        # 요일: Python의 weekday()는 월요일이 0, 일요일이 6
        weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        weekday = weekdays[dt.weekday()]
        
        # 오전/오후 및 12시간제로 변환
        if dt.hour < 12:
            am_pm = "오전"
            hour_12 = dt.hour if dt.hour != 0 else 12
        else:
            am_pm = "오후"
            hour_12 = dt.hour - 12 if dt.hour != 12 else 12
            
        return f"{dt.year}년 {dt.month}월 {dt.day}일 {weekday} {am_pm} {hour_12}:{dt.minute:02d}:{dt.second:02d} GMT+09:00"

    # ---------------------------------------------------------------------
    # 공개 API
    # ---------------------------------------------------------------------
    def get_call_records(self, limit: int = 100) -> pd.DataFrame:
        """
        통화 기록을 조회합니다.
        
        Args:
            limit (int): 반환할 최대 레코드 수
            
        Returns:
            pd.DataFrame: 통화 기록이 포함된 데이터프레임
        """
        if not self.conn and not self.connect_to_db():
            return pd.DataFrame()

        try:
            query = """
                SELECT 
                    Z_PK as id,
                    ZDATE as date_ts,
                    ZDURATION as duration,
                    ZADDRESS as address,
                    CASE ZORIGINATED 
                        WHEN 0 THEN '수신' 
                        WHEN 1 THEN '발신' 
                        ELSE 'N/A' 
                    END AS direction,
                    CASE ZANSWERED 
                        WHEN 0 THEN '아니오' 
                        WHEN 1 THEN '예' 
                        ELSE 'N/A' 
                    END AS answered
                FROM ZCALLRECORD
                ORDER BY ZDATE DESC
                LIMIT ?;
            """
            df = pd.read_sql_query(query, self.conn, params=(limit,))
            
            # 날짜 변환
            df['date'] = df['date_ts'].apply(self._convert_date)
            df['date_formatted'] = df['date'].apply(self._format_korean_date)
            
            # 통화 시간을 보기 좋게 변환 (초 -> 분:초)
            df['duration_formatted'] = df['duration'].apply(
                lambda secs: f"{int(secs // 60)}:{int(secs % 60):02d}" if pd.notna(secs) else ""
            )
            
            return df
        except Exception as e:
            print(f"[Error] 통화 기록 조회 실패: {e}")
            return pd.DataFrame()

    def get_call_statistics(self) -> Dict[str, Any]:
        """
        통화 기록 통계를 계산합니다.
        
        Returns:
            Dict: 통화 통계 정보
        """
        if not self.conn and not self.connect_to_db():
            return {}

        try:
            stats = {}
            
            # 총 통화 수
            query = "SELECT COUNT(*) as count FROM ZCALLRECORD"
            result = self.conn.execute(query).fetchone()
            stats['total_calls'] = result['count'] if result else 0
            
            # 방향별 통화 수
            query = """
                SELECT 
                    CASE ZORIGINATED 
                        WHEN 0 THEN '수신' 
                        WHEN 1 THEN '발신' 
                        ELSE '기타' 
                    END AS direction,
                    COUNT(*) as count
                FROM ZCALLRECORD
                GROUP BY direction
            """
            df = pd.read_sql_query(query, self.conn)
            stats['calls_by_direction'] = df.set_index('direction')['count'].to_dict()
            
            # 응답/부재중 통화 수
            query = """
                SELECT 
                    CASE ZANSWERED 
                        WHEN 0 THEN '부재중' 
                        WHEN 1 THEN '응답' 
                        ELSE '기타' 
                    END AS status,
                    COUNT(*) as count
                FROM ZCALLRECORD
                GROUP BY status
            """
            df = pd.read_sql_query(query, self.conn)
            stats['calls_by_status'] = df.set_index('status')['count'].to_dict()
            
            # 총 통화 시간 (초)
            query = "SELECT SUM(ZDURATION) as total_duration FROM ZCALLRECORD WHERE ZANSWERED = 1"
            result = self.conn.execute(query).fetchone()
            total_seconds = result['total_duration'] if result and result['total_duration'] else 0
            
            # 시간, 분, 초로 변환
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            
            stats['total_duration_seconds'] = total_seconds
            stats['total_duration_formatted'] = f"{hours}시간 {minutes}분 {seconds}초"
            
            return stats
        except Exception as e:
            print(f"[Error] 통화 통계 계산 실패: {e}")
            return {}

    def get_call_detail(self, call_id: int) -> Dict[str, Any]:
        """
        특정 통화 기록의 상세 정보를 조회합니다.
        
        Args:
            call_id (int): 조회할 통화 ID
            
        Returns:
            Dict: 통화 상세 정보
        """
        if not self.conn and not self.connect_to_db():
            return {}

        try:
            query = """
                SELECT 
                    Z_PK as id,
                    ZDATE as date_ts,
                    ZDURATION as duration,
                    ZADDRESS as address,
                    ZSERVICE_PROVIDER as service_provider,
                    ZISO_COUNTRY_CODE as country_code,
                    ZLOCATION as location,
                    ZNAME as name,
                    CASE ZORIGINATED 
                        WHEN 0 THEN '수신' 
                        WHEN 1 THEN '발신' 
                        ELSE 'N/A' 
                    END AS direction,
                    CASE ZANSWERED 
                        WHEN 0 THEN '아니오' 
                        WHEN 1 THEN '예' 
                        ELSE 'N/A' 
                    END AS answered
                FROM ZCALLRECORD
                WHERE Z_PK = ?
            """
            row = self.conn.execute(query, (call_id,)).fetchone()
            
            if not row:
                return {}
                
            # Dict로 변환
            call_detail = dict(row)
            
            # 날짜 변환
            date = self._convert_date(call_detail['date_ts'])
            call_detail['date'] = date
            call_detail['date_formatted'] = self._format_korean_date(date) if date else "날짜 없음"
            
            # 통화 시간 포맷팅
            seconds = call_detail.get('duration', 0) or 0
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            call_detail['duration_formatted'] = f"{minutes}분 {remaining_seconds}초"
            
            return call_detail
        except Exception as e:
            print(f"[Error] 통화 상세 정보 조회 실패: {e}")
            return {}

    def analyze_missing_records(self) -> Dict[str, int]:
        """
        ZCALLRECORD 테이블의 누락된(삭제된) 레코드를 분석합니다.
        
        Returns:
            Dict: 분석 결과 (최대 PK, 실제 레코드 수, 누락된 레코드 수)
        """
        if not self.conn and not self.connect_to_db():
            return {'max_pk': 0, 'actual_count': 0, 'missing_count': 0}

        try:
            # 최대 PK 값
            cursor = self.conn.cursor()
            cursor.execute("SELECT MAX(Z_PK) as max_pk FROM ZCALLRECORD;")
            result = cursor.fetchone()
            max_pk = result['max_pk'] if result and result['max_pk'] else 0
            
            # 실제 레코드 수
            cursor.execute("SELECT COUNT(*) as count FROM ZCALLRECORD;")
            result = cursor.fetchone()
            actual_count = result['count'] if result and result['count'] else 0
            
            # 누락된 레코드 수
            missing_count = max_pk - actual_count
            
            return {
                'max_pk': max_pk,
                'actual_count': actual_count,
                'missing_count': missing_count
            }
        except Exception as e:
            print(f"[Error] 누락 레코드 분석 실패: {e}")
            return {'max_pk': 0, 'actual_count': 0, 'missing_count': 0}

    def get_frequent_contacts(self, limit: int = 10) -> pd.DataFrame:
        """
        가장 자주 통화한 연락처를 조회합니다.
        
        Args:
            limit (int): 반환할 최대 연락처 수
            
        Returns:
            pd.DataFrame: 빈도순으로 정렬된 연락처 목록
        """
        if not self.conn and not self.connect_to_db():
            return pd.DataFrame()

        try:
            query = """
                SELECT 
                    ZADDRESS as address,
                    ZNAME as name,
                    COUNT(*) as call_count,
                    SUM(CASE WHEN ZORIGINATED = 1 THEN 1 ELSE 0 END) as outgoing_count,
                    SUM(CASE WHEN ZORIGINATED = 0 THEN 1 ELSE 0 END) as incoming_count,
                    SUM(ZDURATION) as total_duration
                FROM ZCALLRECORD
                GROUP BY ZADDRESS
                ORDER BY call_count DESC
                LIMIT ?
            """
            df = pd.read_sql_query(query, self.conn, params=(limit,))
            
            # 빈 이름 처리
            df['name'] = df['name'].fillna('')
            
            # 총 통화 시간 포맷팅
            df['total_duration_formatted'] = df['total_duration'].apply(
                lambda secs: f"{int(secs // 60)}분 {int(secs % 60):02d}초" if pd.notna(secs) else "0분 0초"
            )
            
            return df
        except Exception as e:
            print(f"[Error] 빈도 연락처 조회 실패: {e}")
            return pd.DataFrame()

    def get_calls_by_date_range(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        특정 날짜 범위의 통화 기록을 조회합니다.
        
        Args:
            start_date (datetime): 시작 날짜/시간
            end_date (datetime): 종료 날짜/시간
            
        Returns:
            pd.DataFrame: 해당 기간의 통화 기록
        """
        if not self.conn and not self.connect_to_db():
            return pd.DataFrame()

        try:
            # datetime을 iOS 타임스탬프로 변환
            start_ts = start_date.timestamp() - self.IOS_EPOCH
            end_ts = end_date.timestamp() - self.IOS_EPOCH
            
            query = """
                SELECT 
                    Z_PK as id,
                    ZDATE as date_ts,
                    ZDURATION as duration,
                    ZADDRESS as address,
                    ZNAME as name,
                    CASE ZORIGINATED 
                        WHEN 0 THEN '수신' 
                        WHEN 1 THEN '발신' 
                        ELSE 'N/A' 
                    END AS direction,
                    CASE ZANSWERED 
                        WHEN 0 THEN '아니오' 
                        WHEN 1 THEN '예' 
                        ELSE 'N/A' 
                    END AS answered
                FROM ZCALLRECORD
                WHERE ZDATE BETWEEN ? AND ?
                ORDER BY ZDATE DESC
            """
            df = pd.read_sql_query(query, self.conn, params=(start_ts, end_ts))
            
            # 날짜 변환
            df['date'] = df['date_ts'].apply(self._convert_date)
            df['date_formatted'] = df['date'].apply(self._format_korean_date)
            
            # 통화 시간 포맷팅
            df['duration_formatted'] = df['duration'].apply(
                lambda secs: f"{int(secs // 60)}:{int(secs % 60):02d}" if pd.notna(secs) else ""
            )
            
            return df
        except Exception as e:
            print(f"[Error] 날짜 범위 통화 조회 실패: {e}")
            return pd.DataFrame()

    def get_database_metadata(self) -> Dict[str, Any]:
        """
        CallHistory.storedata 데이터베이스의 메타데이터를 조회합니다.
        
        Returns:
            Dict: 메타데이터 정보
        """
        if not self.conn and not self.connect_to_db():
            return {}

        try:
            metadata = {}
            
            # 테이블 목록
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            metadata['tables'] = tables
            
            # Z_PRIMARYKEY 테이블 정보
            if 'Z_PRIMARYKEY' in tables:
                query = "SELECT Z_NAME, Z_MAX FROM Z_PRIMARYKEY ORDER BY Z_NAME;"
                df = pd.read_sql_query(query, self.conn)
                metadata['primary_keys'] = df.set_index('Z_NAME')['Z_MAX'].to_dict()
            
            # 데이터베이스 통계
            table_stats = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                result = cursor.fetchone()
                table_stats[table] = result[0] if result else 0
            metadata['table_counts'] = table_stats
            
            return metadata
        except Exception as e:
            print(f"[Error] 데이터베이스 메타데이터 조회 실패: {e}")
            return {}


# 사용 예시
if __name__ == "__main__":
    # 백업 경로 (예시)
    backup_path = "/path/to/ios/backup"
    
    # 분석기 생성
    analyzer = CallHistoryAnalyzer(backup_path)
    
    # 연결 테스트
    if analyzer.connect_to_db():
        print("데이터베이스 연결 성공!")
        
        # 통화 기록 조회 (최근 10개)
        calls = analyzer.get_call_records(limit=10)
        print(f"최근 통화 기록: {len(calls)}개 조회됨")
        
        # 통계 출력
        stats = analyzer.get_call_statistics()
        print(f"총 통화 수: {stats.get('total_calls', 0)}")
        print(f"총 통화 시간: {stats.get('total_duration_formatted', '0시간 0분 0초')}")
        
        # 연결 종료
        analyzer.close_connection()
    else:
        print("데이터베이스 연결 실패!")