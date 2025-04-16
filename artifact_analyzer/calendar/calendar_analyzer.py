import os
import sqlite3
from datetime import datetime
import pandas as pd

class BackupPathHelper:
    """
    iOS 백업 파일 경로를 찾기 위한 도우미 클래스.
    Manifest.db 파일을 이용하여 백업 파일의 실제 경로를 탐색합니다.
    """
    def __init__(self, backup_path: str):
        """
        백업 경로를 초기화합니다.
        :param backup_path: iOS 백업의 루트 경로
        """
        self.backup_path = backup_path

    def get_file_path_from_manifest(self, relative_path: str) -> str:
        """
        Manifest.db에서 주어진 상대 경로에 해당하는 파일의 해시값을 조회하여
        실제 파일 경로를 반환합니다.
        
        :param relative_path: Manifest.db에서 검색할 상대 파일 경로
        :return: 실제 파일 경로 또는 None (파일을 찾지 못한 경우)
        """
        manifest_path = os.path.join(self.backup_path, "Manifest.db")
        if not os.path.exists(manifest_path):
            print(f"[오류] Manifest.db 파일이 존재하지 않습니다: {manifest_path}")
            return None

        try:
            # with문을 이용하여 안전하게 SQLite 연결을 열고 종료합니다.
            with sqlite3.connect(manifest_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT fileID FROM Files WHERE relativePath = ?", (relative_path,))
                result = cursor.fetchone()

            if result:
                file_hash = result[0]
                file_path = os.path.join(self.backup_path, file_hash[:2], file_hash)
                if os.path.exists(file_path):
                    return file_path
                else:
                    print(f"[경고] Manifest에 등록되었으나 실제 파일이 존재하지 않습니다: {file_path}")
            else:
                print(f"[경고] Manifest에서 해당 상대 경로를 찾을 수 없습니다: {relative_path}")
        except Exception as e:
            print(f"[오류] Manifest.db 검색 오류: {e}")
        return None

class CalendarAnalyser:
    """
    iOS 캘린더 데이터베이스를 분석하는 클래스.
    백업 경로를 통해 캘린더 데이터베이스 파일에 접근하여 이벤트 및 관련 정보를 DataFrame이나 dict 형태로 반환합니다.
    """
    def __init__(self, backup_path: str):
        """
        캘린더 분석기 초기화.
        :param backup_path: iOS 백업의 루트 경로
        """
        self.backup_path = backup_path
        # Manifest 검색 실패 시 사용할 기본 캘린더 DB 경로
        self.default_calendar_db_path = os.path.join(backup_path, "Library", "Calendar", "Calendar.sqlitedb")
        self.conn = None
        self.path_helper = BackupPathHelper(backup_path)

    def connect_to_db(self) -> bool:
        """
        캘린더 데이터베이스에 연결을 시도합니다.
        우선 Manifest.db에서 파일 경로를 찾고, 실패 시 기본 경로를 사용합니다.
        
        :return: 연결 성공 여부 (True/False)
        """
        relative_path = "Library/Calendar/Calendar.sqlitedb"
        calendar_db_path = self.path_helper.get_file_path_from_manifest(relative_path)
        if not calendar_db_path:
            print("[정보] Manifest 검색 실패. 기본 경로 사용:")
            calendar_db_path = self.default_calendar_db_path

        if os.path.exists(calendar_db_path):
            try:
                self.conn = sqlite3.connect(calendar_db_path)
                self.conn.row_factory = sqlite3.Row  # Row 객체를 dict처럼 사용할 수 있음
                print(f"[성공] Calendar 데이터베이스 연결 성공: {calendar_db_path}")
                return True
            except sqlite3.Error as e:
                print(f"[오류] 데이터베이스 연결 오류: {e}")
                return False
        else:
            print("[오류] Calendar 데이터베이스 파일을 찾을 수 없습니다.")
            return False

    def close_connection(self):
        """
        데이터베이스 연결 종료.
        """
        if self.conn:
            self.conn.close()
            self.conn = None

    def _convert_date(self, raw_value) -> datetime:
        """
        캘린더의 날짜 값을 datetime 객체로 변환합니다.
        iOS는 기준 시간(978307200초)을 보정하여 저장합니다.
        값의 크기에 따라 적절하게 단위를 변환합니다.
        
        :param raw_value: 변환 전 날짜 값
        :return: 변환된 datetime 객체 또는 None (변환 실패 시)
        """
        try:
            raw_value = float(raw_value)
        except (ValueError, TypeError):
            return None

        # 값의 크기에 따라 나노초, 밀리초 또는 초 단위로 변환
        if raw_value > 1e12:
            seconds = raw_value / 1e9
        elif raw_value > 1e9:
            seconds = raw_value / 1e3
        else:
            seconds = raw_value

        unix_time_sec = seconds + 978307200  # iOS 기준 시간 보정
        try:
            return datetime.fromtimestamp(unix_time_sec)
        except Exception:
            return None

    def get_events_for_month(self, year: int, month: int) -> pd.DataFrame:
        """
        지정된 연도와 월의 이벤트 목록을 DataFrame으로 반환합니다.
        CalendarItem과 Calendar 테이블을 조인하여 이벤트 세부 정보를 가져옵니다.
        
        :param year: 연도 (예: 2023)
        :param month: 월 (1~12)
        :return: 이벤트 정보를 담은 DataFrame (데이터가 없으면 빈 DataFrame 반환)
        """
        if not self.conn and not self.connect_to_db():
            return pd.DataFrame()

        try:
            from calendar import monthrange
            start_date = datetime(year, month, 1)
            last_day = monthrange(year, month)[1]
            end_date = datetime(year, month, last_day, 23, 59, 59)
            # 저장된 타임스탬프는 보정 전 값이므로 기준 시간 차감
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
            print(f"[오류] 이벤트 조회 오류: {e}")
            return pd.DataFrame()

    def get_event_details(self, event_id: int) -> dict:
        """
        특정 이벤트의 상세 정보를 반환합니다.
        추가로 캘린더 정보(예: 캘린더 제목, 색상 등)를 포함합니다.
        
        :param event_id: 조회할 이벤트의 ROWID
        :return: 이벤트 상세 정보를 담은 dict (없으면 None)
        """
        if not self.conn and not self.connect_to_db():
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
            print(f"[오류] 이벤트 상세 정보 조회 오류: {e}")
            return None

    def get_error_logs(self, event_id: int) -> list:
        """
        Error 테이블에서 해당 이벤트의 오류 로그를 조회합니다.
        
        :param event_id: 캘린더 항목의 ROWID
        :return: 오류 로그 목록 (리스트 형태의 dict)
        """
        try:
            query = "SELECT * FROM Error WHERE calendaritem_owner_id = ?"
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"[오류] Error 로그 조회 오류: {e}")
            return []

    def get_event_actions(self, event_id: int) -> list:
        """
        EventAction 테이블에서 해당 이벤트의 외부 연동 작업 정보를 조회합니다.
        
        :param event_id: 이벤트의 ROWID
        :return: 외부 연동 작업 정보 목록
        """
        try:
            query = "SELECT * FROM EventAction WHERE event_id = ?"
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"[오류] EventAction 조회 오류: {e}")
            return []

    def get_exception_dates(self, event_id: int) -> list:
        """
        반복 이벤트에 대한 예외 날짜 정보를 ExceptionDate 테이블에서 조회합니다.
        날짜 필드는 문자열(YYYY-MM-DD)을 datetime 객체로 변환합니다.
        
        :param event_id: 이벤트의 ROWID
        :return: 예외 날짜 정보 목록
        """
        try:
            query = "SELECT * FROM ExceptionDate WHERE owner_id = ?"
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            if not df.empty and 'date' in df.columns:
                df['date'] = df['date'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d") if isinstance(x, str) else x)
            return df.to_dict('records')
        except Exception as e:
            print(f"[오류] ExceptionDate 조회 오류: {e}")
            return []

    def get_recurrence_info(self, event_id: int) -> list:
        """
        반복 규칙 정보를 Recurrence 테이블에서 조회합니다.
        
        :param event_id: 이벤트의 ROWID
        :return: 반복 규칙 정보 목록
        """
        try:
            query = "SELECT * FROM Recurrence WHERE owner_id = ?"
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"[오류] Recurrence 정보 조회 오류: {e}")
            return []

    def get_participants(self, event_id: int) -> list:
        """
        Participant 테이블에서 이벤트의 참여자 정보를 조회합니다.
        
        :param event_id: 이벤트의 ROWID
        :return: 참여자 정보 목록
        """
        try:
            query = "SELECT * FROM Participant WHERE owner_id = ?"
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"[오류] Participant 조회 오류: {e}")
            return []

    def get_location_info(self, location_id: int) -> list:
        """
        Location 테이블에서 위치 정보를 조회합니다.
        
        :param location_id: 위치의 ROWID
        :return: 위치 정보 목록
        """
        try:
            query = "SELECT * FROM Location WHERE ROWID = ?"
            df = pd.read_sql_query(query, self.conn, params=(location_id,))
            return df.to_dict('records')
        except Exception as e:
            print(f"[오류] Location 정보 조회 오류: {e}")
            return []

    def get_alarms_for_event(self, event_id: int) -> list:
        """
        Alarm 및 AlarmCache 테이블을 조인하여 이벤트와 연결된 알람 정보를 조회합니다.
        알람의 trigger_date, trigger_interval, type, disabled, occurrence_date, fire_date 등의 정보를 포함합니다.
        
        :param event_id: 이벤트의 ROWID
        :return: 알람 정보 목록
        """
        if not self.conn and not self.connect_to_db():
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
            print(f"[오류] 알람 정보 조회 오류: {e}")
            return []

    def get_attachments_for_event(self, event_id: int) -> list:
        """
        Attachment 및 AttachmentFile 테이블을 조인하여 이벤트와 연결된 첨부파일 정보를 조회합니다.
        파일의 메타데이터(파일 이름, URL, 경로 등)를 반환합니다.
        
        :param event_id: Attachment 테이블의 owner_id에 해당하는 이벤트의 ROWID
        :return: 첨부파일 정보 목록
        """
        if not self.conn and not self.connect_to_db():
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
            print(f"[오류] 첨부파일 정보 조회 오류: {e}")
            return []