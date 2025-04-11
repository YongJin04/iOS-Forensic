import os
import re
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

class BackupPathHelper:
    """iOS 백업 파일 경로를 찾는 도우미 클래스"""
    
    def __init__(self, backup_path):
        self.backup_path = backup_path
        
    def get_file_path_from_manifest(self, relative_path):
        """
        Manifest.db 파일에서 상대 경로에 해당하는 해시 파일명을 찾아 전체 경로 반환
        
        iOS 백업은 파일이 backup_path/<해시값의 처음 두 글자>/<전체 해시> 형식으로 저장됩니다.
        """
        manifest_path = os.path.join(self.backup_path, "Manifest.db")
        if not os.path.exists(manifest_path):
            print(f"Manifest.db 파일이 존재하지 않습니다: {manifest_path}")
            return None
            
        try:
            conn = sqlite3.connect(manifest_path)
            cursor = conn.cursor()
            
            # Files 테이블에서 상대 경로와 일치하는 파일 검색
            cursor.execute(
                "SELECT fileID FROM Files WHERE relativePath = ?",
                (relative_path,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                file_hash = result[0]
                # 해시 파일명의 처음 두 글자를 하위 디렉토리로 사용함
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


class SMSAnalyser:
    def __init__(self, backup_path):
        self.backup_path = backup_path
        # 기본 경로 설정 (Manifest 검색에 실패한 경우 대비)
        self.default_sms_db_path = os.path.join(backup_path, "HomeDomain", "Library", "SMS", "sms.db")
        self.conn = None
        # BackupPathHelper 인스턴스 생성 (Manifest.db를 통한 경로 검색)
        self.path_helper = BackupPathHelper(backup_path)
        
    def connect_to_db(self):
        """SMS 데이터베이스에 연결합니다."""
        # 우선 Manifest.db를 이용해 SMS 데이터베이스 파일 경로를 찾습니다.
        relative_path = "Library/SMS/sms.db"
        sms_db_path = self.path_helper.get_file_path_from_manifest(relative_path)
        
        if not sms_db_path:
            # Manifest 검색에 실패하면 기본 경로 사용
            print("Manifest 검색 실패. 기본 경로 사용:")
            sms_db_path = self.default_sms_db_path
            
        if os.path.exists(sms_db_path):
            try:
                self.conn = sqlite3.connect(sms_db_path)
                self.conn.row_factory = sqlite3.Row
                print(f"SMS 데이터베이스 연결 성공: {sms_db_path}")
                return True
            except sqlite3.Error as e:
                print(f"데이터베이스 연결 오류: {e}")
                return False
        else:
            print("SMS 데이터베이스 파일을 찾을 수 없습니다.")
            return False
    
    def close_connection(self):
        """데이터베이스 연결을 종료합니다."""
        if self.conn:
            self.conn.close()
    
    def format_phone_number(self, phone):
        """전화번호 포맷 함수 (스팸 기능 제거, 다양한 형식에 대해 깔끔하게 변환)"""
        cleaned = re.sub(r'[^\d+]', '', phone)
        if cleaned.startswith('+'):
            return cleaned
        else:
            digits = re.sub(r'\D', '', phone)
            if digits.startswith("02"):
                if len(digits) == 9:
                    return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
                elif len(digits) == 10:
                    return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
                else:
                    return digits
            else:
                if digits.startswith("010"):
                    if len(digits) == 10:
                        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
                    elif len(digits) == 11:
                        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                    else:
                        return digits
                else:
                    if len(digits) == 10:
                        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
                    elif len(digits) == 11:
                        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                    else:
                        return digits
    
    def hyperlink_urls(self, text):
        """메시지 내용 중 URL을 하이퍼링크로 변환하는 함수"""
        if not text:
            return ""
        url_pattern = re.compile(r'((https?://|www\.)[^\s]+)')
        def replace(match):
            url = match.group(0)
            if url.startswith("www."):
                url = "http://" + url
            return f"<a href='{url}'>{match.group(0)}</a>"
        return url_pattern.sub(replace, text)
    
    def get_conversations(self):
        """모든 대화 상대 목록을 가져옵니다."""
        if not self.conn:
            if not self.connect_to_db():
                return []
        
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT DISTINCT h.ROWID as handle_rowid, h.id as handle_id 
            FROM message m 
            JOIN handle h ON m.handle_id = h.ROWID 
            ORDER BY h.id
            """
            cursor.execute(query)
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    'handle_rowid': row['handle_rowid'],
                    'handle_id': row['handle_id'],
                    'formatted_id': self.format_phone_number(row['handle_id'])
                })
            return conversations
        except sqlite3.Error as e:
            print(f"대화 목록 조회 오류: {e}")
            return []
    
    def get_conversation_messages(self, handle_rowid):
        """특정 대화 상대와의 메시지를 가져옵니다."""
        if not self.conn:
            if not self.connect_to_db():
                return []
        
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT message.ROWID, message.guid, message.text, message.date, message.is_from_me 
            FROM message 
            WHERE message.handle_id = ? 
            ORDER BY message.date ASC
            """
            cursor.execute(query, (handle_rowid,))
            messages = []
            
            for row in cursor.fetchall():
                raw_value = float(row["date"])
                if raw_value > 1e12:
                    seconds = raw_value / 1e9
                elif raw_value > 1e9:
                    seconds = raw_value / 1e3
                else:
                    seconds = raw_value
                
                unix_time_sec = seconds + 978307200  # iOS 기준 시간 보정
                date_obj = datetime.fromtimestamp(unix_time_sec)
                
                # 첨부파일 확인 (간단한 예시)
                attachment_path = None
                if row["text"] and row["text"].strip() == "사진":
                    attachment_path = self.get_attachment_path(row["guid"])
                
                messages.append({
                    'rowid': row['ROWID'],
                    'guid': row['guid'],
                    'text': row['text'] if row['text'] else "",
                    'date': date_obj,
                    'date_str': date_obj.strftime('%Y년 %m월 %d일 %H:%M:%S'),
                    'is_from_me': bool(row['is_from_me']),
                    'direction': '발신' if bool(row['is_from_me']) else '수신',
                    'attachment_path': attachment_path
                })
            
            return messages
        except sqlite3.Error as e:
            print(f"메시지 조회 오류: {e}")
            return []
    
    def get_attachment_path(self, message_guid):
        """메시지의 첨부파일 경로를 가져옵니다."""
        if not self.conn:
            if not self.connect_to_db():
                return None
        
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT attachment.filename
            FROM message
            JOIN message_attachment_join
                ON message.ROWID = message_attachment_join.message_id
            JOIN attachment
                ON attachment.ROWID = message_attachment_join.attachment_id
            WHERE message.guid = ?
            LIMIT 1
            """
            cursor.execute(query, (message_guid,))
            row = cursor.fetchone()
            if row and row["filename"]:
                return row["filename"]
            return None
        except sqlite3.Error as e:
            print(f"첨부파일 조회 오류: {e}")
            return None
    
    def get_all_sms_messages(self, limit=1000):
        """모든 SMS 메시지를 가져옵니다."""
        if not self.conn:
            if not self.connect_to_db():
                return pd.DataFrame()
        
        try:
            query = """
            SELECT 
                message.rowid,
                message.date,
                message.text,
                message.is_from_me,
                handle.id as contact_id
            FROM 
                message
            LEFT JOIN 
                handle ON message.handle_id = handle.rowid
            ORDER BY 
                message.date DESC
            LIMIT ?
            """
            df = pd.read_sql_query(query, self.conn, params=(limit,))
            
            def convert_date(date_value):
                raw_value = float(date_value)
                if raw_value > 1e12:
                    seconds = raw_value / 1e9
                elif raw_value > 1e9:
                    seconds = raw_value / 1e3
                else:
                    seconds = raw_value
                unix_time_sec = seconds + 978307200
                return datetime.fromtimestamp(unix_time_sec)
            
            df['date'] = df['date'].apply(convert_date)
            df['direction'] = df['is_from_me'].apply(lambda x: '발신' if x == 1 else '수신')
            df['formatted_contact'] = df['contact_id'].apply(self.format_phone_number)
            return df
        except Exception as e:
            print(f"전체 SMS 메시지 조회 오류: {e}")
            return pd.DataFrame()
    
    def get_sms_stats(self, df=None):
        """SMS 통계 정보를 가져옵니다."""
        if df is None:
            df = self.get_all_sms_messages()
        
        if df.empty:
            return {
                'total': 0,
                'sent': 0,
                'received': 0,
                'contacts': 0
            }
        
        stats = {
            'total': len(df),
            'sent': len(df[df['direction'] == '발신']),
            'received': len(df[df['direction'] == '수신']),
            'contacts': df['contact_id'].nunique()
        }
        
        return stats