import os
import sqlite3
import re
from datetime import datetime
import pandas as pd

class BackupPathHelper:
    """iOS 백업 파일 경로를 찾는 도우미 클래스 (Manifest.db 이용)"""
    def __init__(self, backup_path):
        self.backup_path = backup_path

    def get_file_path_from_manifest(self, relative_path):
        manifest_path = os.path.join(self.backup_path, "Manifest.db")
        if not os.path.exists(manifest_path):
            print(f"Manifest.db 파일이 존재하지 않습니다: {manifest_path}")
            return None
        try:
            conn = sqlite3.connect(manifest_path)
            cursor = conn.cursor()
            cursor.execute("SELECT fileID FROM Files WHERE relativePath = ?", (relative_path,))
            result = cursor.fetchone()
            conn.close()
            if result:
                file_hash = result[0]
                file_path = os.path.join(self.backup_path, file_hash[:2], file_hash)
                if os.path.exists(file_path):
                    return file_path
                else:
                    print(f"Manifest에 등록되었으나 실제 파일이 존재하지 않습니다: {file_path}")
            else:
                print(f"Manifest에서 해당 상대 경로를 찾을 수 없습니다: {relative_path}")
        except Exception as e:
            print(f"Manifest.db 검색 오류: {str(e)}")
        return None

class CalendarAnalyser:
    def __init__(self, backup_path):
        self.backup_path = backup_path
        # 기본 경로: Manifest 검색 실패 시 사용
        self.default_calendar_db_path = os.path.join(backup_path, "Library", "Calendar", "Calendar.sqlitedb")
        self.conn = None
        self.path_helper = BackupPathHelper(backup_path)

    def connect_to_db(self):
        """캘린더 데이터베이스에 연결합니다."""
        relative_path = "Library/Calendar/Calendar.sqlitedb"
        calendar_db_path = self.path_helper.get_file_path_from_manifest(relative_path)
        if not calendar_db_path:
            print("Manifest 검색 실패. 기본 경로 사용:")
            calendar_db_path = self.default_calendar_db_path
        if os.path.exists(calendar_db_path):
            try:
                self.conn = sqlite3.connect(calendar_db_path)
                self.conn.row_factory = sqlite3.Row
                print(f"Calendar 데이터베이스 연결 성공: {calendar_db_path}")
                return True
            except sqlite3.Error as e:
                print(f"데이터베이스 연결 오류: {e}")
                return False
        else:
            print("Calendar 데이터베이스 파일을 찾을 수 없습니다.")
            return False

    def close_connection(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()

    def _convert_date(self, raw_value):
        """
        캘린더의 날짜 값을 datetime 객체로 변환.
        SMS와 유사하게 iOS 기준(978307200) 보정 및 값의 크기에 따라 변환합니다.
        """
        try:
            raw_value = float(raw_value)
        except Exception:
            return None
        if raw_value > 1e12:
            seconds = raw_value / 1e9
        elif raw_value > 1e9:
            seconds = raw_value / 1e3
        else:
            seconds = raw_value
        unix_time_sec = seconds + 978307200
        try:
            return datetime.fromtimestamp(unix_time_sec)
        except Exception:
            return None

    def get_events_for_month(self, year, month):
        """
        지정된 년, 월의 이벤트 목록을 DataFrame으로 반환합니다.
        CalendarItem 테이블과 Calendar 테이블을 조인하여, 이벤트 제목, 시작/종료 시간, 
        전체 일정 여부, 캘린더 정보 등 포렌식 분석에 유용한 열을 함께 가져옵니다.
        """
        if not self.conn:
            if not self.connect_to_db():
                return pd.DataFrame()

        try:
            from calendar import monthrange
            start_date = datetime(year, month, 1)
            last_day = monthrange(year, month)[1]
            end_date = datetime(year, month, last_day, 23, 59, 59)
            # iOS 저장 형식에 맞추어 역산 (저장된 값은 보정 전의 timestamp)
            start_timestamp = start_date.timestamp() - 978307200
            end_timestamp = end_date.timestamp() - 978307200

            query = """
            SELECT ci.ROWID as event_id, ci.summary, ci.start_date, ci.end_date, ci.all_day, 
                   ci.location_id, ci.description, c.title as calendar_title, c.color, c.symbolic_color_name
            FROM CalendarItem ci
            LEFT JOIN Calendar c ON ci.calendar_id = c.ROWID
            WHERE ci.start_date BETWEEN ? AND ?
            ORDER BY ci.start_date ASC;
            """
            df = pd.read_sql_query(query, self.conn, params=(start_timestamp, end_timestamp))
            df['start_date'] = df['start_date'].apply(self._convert_date)
            df['end_date'] = df['end_date'].apply(self._convert_date)
            return df
        except Exception as e:
            print(f"이벤트 조회 오류: {e}")
            return pd.DataFrame()

    def get_event_details(self, event_id):
        """
        특정 이벤트의 상세 정보를 반환합니다.
        추가로 캘린더 이름, 색상 등 캘린더 관련 정보를 포함합니다.
        """
        if not self.conn:
            if not self.connect_to_db():
                return None
        try:
            query = """
            SELECT ci.*, c.title as calendar_title, c.color, c.symbolic_color_name
            FROM CalendarItem ci
            LEFT JOIN Calendar c ON ci.calendar_id = c.ROWID
            WHERE ci.ROWID = ?
            """
            cursor = self.conn.cursor()
            cursor.execute(query, (event_id,))
            row = cursor.fetchone()
            if row:
                event = dict(row)
                event['start_date'] = self._convert_date(event['start_date'])
                event['end_date'] = self._convert_date(event['end_date'])
                return event
            return None
        except sqlite3.Error as e:
            print(f"이벤트 상세 정보 조회 오류: {e}")
            return None
        
    def get_error_logs(self, event_id):
        """
        Error TABLE에서 해당 이벤트(캘린더 항목)의 오류 로그를 조회합니다.
        """
        try:
            query = "SELECT * FROM Error WHERE calendaritem_owner_id = ?"
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"Error 로그 조회 오류: {e}")
            return []
        
    def get_event_actions(self, event_id):
        """
        EventAction TABLE에서 해당 이벤트의 외부 연동 작업 정보를 조회합니다.
        """
        try:
            query = "SELECT * FROM EventAction WHERE event_id = ?"
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"EventAction 조회 오류: {e}")
            return []
        
    def get_exception_dates(self, event_id):
        """
        ExceptionDate TABLE에서 반복 이벤트에 대해 예외 날짜 정보를 조회합니다.
        """
        try:
            query = "SELECT * FROM ExceptionDate WHERE owner_id = ?"
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            # 예: 날짜 필드를 datetime으로 변환 (필요시 형식 조정)
            df['date'] = df['date'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d") if isinstance(x, str) else x)
            return df.to_dict('records')
        except Exception as e:
            print(f"ExceptionDate 조회 오류: {e}")
            return []
        
    def get_recurrence_info(self, event_id):
        """
        Recurrence TABLE에서 해당 이벤트의 반복 규칙 정보를 조회합니다.
        """
        try:
            query = "SELECT * FROM Recurrence WHERE owner_id = ?"
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"Recurrence 정보 조회 오류: {e}")
            return []
        
    def get_participants(self, event_id):
        """
        Participant TABLE에서 해당 이벤트의 참여자 정보를 조회합니다.
        """
        try:
            query = "SELECT * FROM Participant WHERE owner_id = ?"
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"Participant 조회 오류: {e}")
            return []
    
    def get_location_info(self, location_id):
        """
        Location TABLE에서 위치 정보를 조회합니다.
        """
        try:
            query = "SELECT * FROM Location WHERE ROWID = ?"
            df = pd.read_sql_query(query, self.conn, params=(location_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"Location 정보 조회 오류: {e}")
            return []

    def get_alarms_for_event(self, event_id):
        """
        주어진 이벤트와 연결된 알람 정보를 반환합니다.
        Alarm, AlarmCache 테이블의 데이터를 이용하여 알람의 trigger_date, trigger_interval,
        type, disabled, occurrence_date, fire_date 등의 정보를 포함합니다.
        """
        if not self.conn:
            if not self.connect_to_db():
                return []
        try:
            query = """
            SELECT a.ROWID as alarm_id, a.trigger_date, a.trigger_interval, a.type, a.disabled,
                   ac.occurrence_date, ac.fire_date
            FROM Alarm a
            LEFT JOIN AlarmCache ac ON a.ROWID = ac.alarm_id
            WHERE ac.event_id = ?
            ORDER BY a.trigger_date ASC;
            """
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            if not df.empty:
                df['trigger_date'] = df['trigger_date'].apply(self._convert_date)
                df['occurrence_date'] = df['occurrence_date'].apply(self._convert_date)
                df['fire_date'] = df['fire_date'].apply(self._convert_date)
            return df.to_dict('records')
        except Exception as e:
            print(f"알람 정보 조회 오류: {e}")
            return []

    def get_attachments_for_event(self, event_id):
        """
        주어진 이벤트와 연결된 첨부파일 정보를 반환합니다.
        Attachment, AttachmentFile 테이블을 조인하여 파일의 메타데이터(파일 이름, URL, 경로 등)를 가져옵니다.
        여기서 event_id는 Attachment 테이블의 owner_id와 매핑된다고 가정합니다.
        """
        if not self.conn:
            if not self.connect_to_db():
                return []
        try:
            query = """
            SELECT af.ROWID as file_rowid, af.external_id, af.url, af.UUID, af.format, af.flags,
                   af.filename, af.local_path, af.file_size
            FROM AttachmentFile af
            JOIN Attachment a ON af.ROWID = a.file_id
            WHERE a.owner_id = ?
            ORDER BY af.filename ASC;
            """
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"첨부파일 정보 조회 오류: {e}")
            return []