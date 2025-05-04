"""
CallHistoryAnalyzer 클래스
 - iOS 백업에서 CallHistory.storedata 파일을 로드하여 분석
 - ZCALLRECORD 테이블의 통화 기록을 처리
 - 삭제된 통화 기록 분석 기능 포함
"""

import os
import sqlite3
from datetime import datetime
from artifact_analyzer.call.backuphelper import BackupPathHelper

class CallRecord:
    """통화 기록 데이터를 저장하는 클래스"""
    
    def __init__(self, z_pk, zdate, zduration, zaddress, zoriginated, zanswered):
        self.z_pk = z_pk
        self.raw_zdate = zdate
        self.duration = zduration
        self.address = zaddress
        self.originated = zoriginated  # 0: 수신, 1: 발신
        self.answered = zanswered  # 0: No, 1: Yes
        
    @property
    def direction(self):
        """통화 방향을 반환 (수신/발신)"""
        return "발신" if self.originated == 1 else "수신"
    
    @property
    def is_answered(self):
        """통화 응답 여부를 반환"""
        return "Yes" if self.answered == 1 else "No"
    
    @property
    def call_date(self):
        """통화 시간을 한국 형식으로 변환하여 반환"""
        return format_korean_date(self.raw_zdate)
    
    def get_formatted_details(self):
        """통화 기록의 상세 정보를 포맷팅하여 반환"""
        details = f"통화 번호: {self.address}\n"
        details += f"통화 시간: {self.call_date}\n"
        details += f"통화 방향: {self.direction}\n"
        details += f"통화 시간: {self.duration}초\n"
        details += f"응답 여부: {self.is_answered}\n"
        details += f"레코드 ID: {self.z_pk}\n"
        
        return details

# Mac epoch (2001-01-01)와 Unix epoch (1970-01-01)의 차이는 978307200초
MAC_EPOCH_OFFSET = 978307200

def format_korean_date(zdate):
    """
    ZDATE (Mac epoch 기준) 값을 받아,  
    "YYYY년 M월 D일 요일 오전/오후 h:mm:ss GMT+09:00" 형식의 문자열로 변환합니다.
    """
    ts = zdate + MAC_EPOCH_OFFSET
    dt = datetime.fromtimestamp(ts)
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

class CallHistoryAnalyzer:
    """iOS 통화 기록 분석기 클래스"""
    
    def __init__(self, backup_path):
        """
        초기화 함수
        
        Args:
            backup_path: iOS 백업 경로
        """
        self.backup_path = backup_path
        self.db_path = None
        self.call_records = []
        self.max_pk = 0
        self.record_count = 0
        
    def find_callhistory_database(self):
        """
        백업 경로에서 CallHistory.storedata 파일을 찾음

        Returns:
            tuple: (성공 여부, 메시지)
        """
        if not self.backup_path:
            return False, "백업 경로가 설정되지 않았습니다."

        backup_helper = BackupPathHelper(self.backup_path)
        manifest_path = os.path.join(self.backup_path, "Manifest.db")

        if not os.path.exists(manifest_path):
            return False, "Manifest.db 파일을 찾을 수 없습니다."

        callhistory_paths = [
            "Library/CallHistoryDB/CallHistory.storedata",
            "private/var/mobile/Library/CallHistoryDB/CallHistory.storedata",
            "HomeDomain/Library/CallHistoryDB/CallHistory.storedata"
        ]

        for path in callhistory_paths:
            file_path = backup_helper.get_file_path_from_manifest(path)
            if file_path and os.path.exists(file_path):
                return True, "CallHistory.storedata 파일을 찾았습니다."

        return False, "CallHistory.storedata 파일을 찾을 수 없습니다."

    
    def load_call_records(self):
        """
        통화 기록 데이터 로드
        
        Returns:
            tuple: (성공 여부, 메시지)
        """
        if not self.db_path:
            success, message = self.find_callhistory_database()
            if not success:
                return False, message
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # ZCALLRECORD 테이블에서 통화 기록 데이터 가져오기
            query = """
                SELECT 
                    Z_PK,
                    ZDATE,
                    ZDURATION,
                    ZADDRESS,
                    ZORIGINATED,
                    ZANSWERED
                FROM ZCALLRECORD
                ORDER BY ZDATE DESC;
            """
            cursor.execute(query)
            records = cursor.fetchall()
            
            # 최대 PK 값과 레코드 수 가져오기 (삭제 분석용)
            cursor.execute("SELECT MAX(Z_PK) FROM ZCALLRECORD;")
            self.max_pk = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM ZCALLRECORD;")
            self.record_count = cursor.fetchone()[0] or 0
            
            conn.close()
            
            # 통화 기록 객체 생성
            self.call_records = []
            for record in records:
                z_pk, zdate, zduration, zaddress, zoriginated, zanswered = record
                call_record = CallRecord(z_pk, zdate, zduration, zaddress, zoriginated, zanswered)
                self.call_records.append(call_record)
            
            return True, f"{len(self.call_records)}개의 통화 기록을 로드했습니다."
        except Exception as e:
            return False, f"통화 기록 로드 중 오류 발생: {str(e)}"
    
    def get_deleted_record_info(self):
        """
        삭제된 통화 기록 분석 정보 반환
        
        Returns:
            dict: 분석 정보 (최대 PK, 총 레코드 수, 삭제된 레코드 수)
        """
        missing_count = self.max_pk - self.record_count if self.max_pk and self.record_count else 0
        
        return {
            "max_pk": self.max_pk,
            "record_count": self.record_count,
            "missing_count": missing_count
        }
    
    def search_call_records(self, search_query="", call_type=None, date_range=None):
        """
        통화 기록 검색
        
        Args:
            search_query: 검색어 (전화번호, 시간 등)
            call_type: 통화 유형 필터 ("모든 통화", "수신 통화", "발신 통화", "부재중 통화")
            date_range: 날짜 범위 필터
            
        Returns:
            list: 검색 조건에 맞는 CallRecord 객체 리스트
        """
        if not self.call_records:
            return []
        
        # 기본 결과는 모든 기록
        filtered_records = self.call_records
        
        # 검색어 필터링
        if search_query:
            search_query = search_query.lower()
            filtered_records = [record for record in filtered_records if 
                               (search_query in record.address.lower() or 
                                search_query in record.call_date.lower() or 
                                search_query in record.direction.lower())]
        
        # 통화 유형 필터링
        if call_type and call_type != "모든 통화":
            if call_type == "수신 통화":
                filtered_records = [record for record in filtered_records if record.originated == 0 and record.answered == 1]
            elif call_type == "발신 통화":
                filtered_records = [record for record in filtered_records if record.originated == 1]
            elif call_type == "부재중 통화":
                filtered_records = [record for record in filtered_records if record.originated == 0 and record.answered == 0]
        
        # 날짜 범위 필터링 (간단한 구현 - 실제로는 더 복잡할 수 있음)
        if date_range and date_range != "전체":
            now = datetime.now()
            today_start = datetime(now.year, now.month, now.day).timestamp() - MAC_EPOCH_OFFSET
            yesterday_start = today_start - 86400  # 하루는 86400초
            
            if date_range == "오늘":
                filtered_records = [record for record in filtered_records if record.raw_zdate >= today_start]
            elif date_range == "어제":
                filtered_records = [record for record in filtered_records if yesterday_start <= record.raw_zdate < today_start]
            # 이번 주, 이번 달 등의 필터링도 필요에 따라 추가할 수 있음
        
        return filtered_records
    
    def get_call_statistics(self):
        """
        통화 기록 통계 정보 반환
        
        Returns:
            dict: 통계 정보 (총 통화 수, 발신 통화 수, 수신 통화 수, 부재중 통화 수)
        """
        if not self.call_records:
            return {
                "total_calls": 0,
                "outgoing_calls": 0,
                "incoming_calls": 0,
                "missed_calls": 0,
                "total_duration": 0,
                "avg_duration": 0,
                "max_duration": 0,
                "top_called_number": None
            }
        
        total_calls = len(self.call_records)
        outgoing_calls = sum(1 for record in self.call_records if record.originated == 1)
        incoming_calls = sum(1 for record in self.call_records if record.originated == 0 and record.answered == 1)
        missed_calls = sum(1 for record in self.call_records if record.originated == 0 and record.answered == 0)
        
        # 통화 시간 관련 통계
        total_duration = sum(record.duration for record in self.call_records)
        avg_duration = total_duration / total_calls if total_calls > 0 else 0
        max_duration = max((record.duration for record in self.call_records), default=0)
        
        # 가장 많이 통화한 번호 찾기
        number_count = {}
        for record in self.call_records:
            number_count[record.address] = number_count.get(record.address, 0) + 1
        
        top_called_number = max(number_count.items(), key=lambda x: x[1])[0] if number_count else None
        
        return {
            "total_calls": total_calls,
            "outgoing_calls": outgoing_calls,
            "incoming_calls": incoming_calls,
            "missed_calls": missed_calls,
            "total_duration": total_duration,
            "avg_duration": avg_duration,
            "max_duration": max_duration,
            "top_called_number": top_called_number
        }
    
    def get_calls_by_date(self):
        """
        날짜별 통화 횟수 집계를 반환
        
        Returns:
            dict: {날짜: 통화 횟수} 형태의 딕셔너리
        """
        date_counts = {}
        for record in self.call_records:
            date_str = format_korean_date(record.raw_zdate).split()[0]  # YYYY년 M월 D일 추출
            date_counts[date_str] = date_counts.get(date_str, 0) + 1
        
        return date_counts
    
    def get_calls_by_type(self):
        """
        유형별 통화 횟수 집계를 반환
        
        Returns:
            dict: 유형별 통화 횟수
        """
        incoming_answered = sum(1 for record in self.call_records if record.originated == 0 and record.answered == 1)
        outgoing = sum(1 for record in self.call_records if record.originated == 1)
        missed = sum(1 for record in self.call_records if record.originated == 0 and record.answered == 0)
        
        return {
            "수신 통화": incoming_answered,
            "발신 통화": outgoing,
            "부재중 통화": missed
        }