import os
import re
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib

# iOS 백업 파일 내에서 특정 파일의 실제 경로를 찾아주는 도우미 클래스입니다.
class BackupPathHelper:
    """iOS 백업 파일 경로를 찾는 도우미 클래스"""
    
    def __init__(self, backup_path):
        # 백업 파일들이 저장된 기본 디렉토리 경로
        self.backup_path = backup_path
        
    def get_file_path_from_manifest(self, domain, relative_path):
        """
        Manifest.db 파일에서 상대 경로에 해당하는 해시 파일명을 찾아 전체 경로를 반환합니다.
        iOS 백업은 파일이 backup_path/<해시값의 처음 두 글자>/<전체 해시> 형식으로 저장됩니다.
        
        인자:           
          domain: Manifest.db에서 검색할 파일의 App Domain
          relative_path: Manifest.db에서 검색할 파일의 상대 경로
        반환값:
          실제 파일 경로 (존재하지 않을 경우 None 반환)
        """
        # Manifest.db 파일의 경로 생성
        manifest_path = os.path.join(self.backup_path, "Manifest.db")
        if not os.path.exists(manifest_path):
            print(f"Manifest.db 파일이 존재하지 않습니다: {manifest_path}")
            return None
            
        try:
            # SQLite를 통해 Manifest.db에 연결
            conn = sqlite3.connect(manifest_path)
            cursor = conn.cursor()
            
            # Files 테이블에서 지정한 상대 경로와 일치하는 파일ID(해시)를 검색
            cursor.execute(
                "SELECT fileID FROM Files WHERE domain = ? AND relativePath = ?",
                (domain, relative_path,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                file_hash = result[0]
                # 해시 파일명의 처음 두 글자를 하위 디렉토리로 사용하여 전체 파일 경로를 구성
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

# KakaoTalk 메신저 데이터를 분석하고 처리하는 클래스입니다.
class KakaoTalkAnalyzer:
    def __init__(self, backup_path):
        # 백업 파일 경로를 저장
        self.backup_path = backup_path
        # Manifest 검색 실패 시 사용될 기본 KakaoTalk 데이터베이스 경로 설정
        self.default_message_db_path = os.path.join(backup_path, "AppDomain-com.iwilab.KakaoTalk", "Library", "PrivateDocuments", "Message.sqlite")
        self.default_talk_db_path = os.path.join(backup_path, "AppDomain-com.iwilab.KakaoTalk", "Library", "PrivateDocuments", "Talk.sqlite")
        self.conn_message_db = None # Message.sqlite 연결 객체
        self.conn_talk_db = None # Talk.sqlite 연결 객체
        self.my_id = None # My KakaoTalk ID (수신 메시지와 발신 메시지를 구분하기 위함)
        # Manifest.db를 통해 경로를 검색하기 위한 BackupPathHelper 인스턴스 생성
        self.path_helper = BackupPathHelper(backup_path)

    def get_my_id(self):
        """내 KakaoTalk ID 가져오기"""
        if not self.conn_talk_db:
            if not self.connect_to_talk_db():
                return ''
            
        try:
            cursor = self.conn_talk_db.cursor()
            # ZFRIENDTYPE이 1로 설정된(나)의 ZID를 가져옵니다다
            query = """
            SELECT DISTINCT ZID
            FROM ZUSER 
            WHERE ZFRIENDTYPE = 1
            """
            cursor.execute(query)       
            row = cursor.fetchone()
            return row['ZID']
        except sqlite3.Error as e:
            print(f"내 KakaoTalk 사용자 ID 조회 오류 발생생: {e}")
            return ''
        
        
    def connect_to_message_db(self):
        """KakaoTalk 데이터베이스에 연결합니다."""
        # Manifest.db를 이용해 KakaoTalk 데이터베이스 파일의 실제 경로를 찾습니다.
        domain_path = 'AppDomain-com.iwilab.KakaoTalk'
        message_relative_path = 'Library/PrivateDocuments/Message.sqlite'
        message_db_path = self.path_helper.get_file_path_from_manifest(domain_path, message_relative_path)
        
        if not message_db_path:
            # Manifest 검색에 실패하면 기본 경로를 사용합니다.
            print("Manifest에서 Message.sqlite를 찾을 수 없음. 기본 경로 사용:" + str(self.default_message_db_path))
            message_db_path = self.default_message_db_path
          
        if os.path.exists(message_db_path):
            try:
                # SQLite 데이터베이스 연결 및 컬럼 이름 기반 접근을 위해 row_factory 설정
                self.conn_message_db = sqlite3.connect(message_db_path)
                self.conn_message_db.row_factory = sqlite3.Row
                print(f"Message.sqlite 데이터베이스 연결 성공: {message_db_path}")
                return True
            except sqlite3.Error as e:
                print(f"Message.sqlite 데이터베이스 연결 오류: {e}")
                return False
        else:
            print("Message.sqlite 데이터베이스 파일을 찾을 수 없습니다.")
            return False
        
    def connect_to_talk_db(self):
        """KakaoTalk 데이터베이스에 연결합니다."""
        # Manifest.db를 이용해 KakaoTalk 데이터베이스 파일의 실제 경로를 찾습니다.
        domain_path = 'AppDomain-com.iwilab.KakaoTalk'
        talk_relative_path = 'Library/PrivateDocuments/Talk.sqlite'
        talk_db_path = self.path_helper.get_file_path_from_manifest(domain_path, talk_relative_path)
        
        if not talk_db_path:
            # Manifest 검색에 실패하면 기본 경로를 사용합니다.
            print("Manifest에서 Talk.sqlite를 찾을 수 없음. 기본 경로 사용:" + str(self.default_talk_db_path))
            talk_db_path = self.default_talk_db_path
                      
        if os.path.exists(talk_db_path):
            try:
                # SQLite 데이터베이스 연결 및 컬럼 이름 기반 접근을 위해 row_factory 설정
                self.conn_talk_db = sqlite3.connect(talk_db_path)
                self.conn_talk_db.row_factory = sqlite3.Row
                print(f"Talk.sqlite 데이터베이스 연결 성공: {talk_db_path}")
                return True
            except sqlite3.Error as e:
                print(f"Talk.sqlite 데이터베이스 연결 오류: {e}")
                return False
        else:
            print("Talk.sqlite 데이터베이스 파일을 찾을 수 없습니다.")
            return False
    
    def close_connection_message_db(self):
        """Message.sqlite 데이터베이스 연결을 종료합니다."""
        if self.conn_message_db:
            self.conn_message_db.close()

    def close_connection_talk_db(self):
        """Talk.sqlite 데이터베이스 연결을 종료합니다."""
        if self.conn_talk_db:
            self.conn_talk_db.close()
    
    def format_phone_number(self, phone):
        """
        전화번호 포맷 함수
        - 불필요한 문자(공백, 하이픈 등)를 제거하고,
        - 국가 코드나 지역 번호(예: 02, 010)에 따라 적절한 하이픈을 추가해 포맷팅합니다.
        """
        # 숫자와 '+' 기호 이외의 문자를 제거
        cleaned = re.sub(r'[^\d+]', '', phone)
        if cleaned.startswith('+'):
            return cleaned
        else:
            # 모든 숫자만 남김
            digits = re.sub(r'\D', '', phone)
            # 서울 지역번호인 "02"인 경우
            if digits.startswith("02"):
                if len(digits) == 9:
                    return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
                elif len(digits) == 10:
                    return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
                else:
                    return digits
            else:
                # 휴대전화 번호 "010"인 경우
                if digits.startswith("010"):
                    if len(digits) == 10:
                        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
                    elif len(digits) == 11:
                        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                    else:
                        return digits
                else:
                    # 그 외의 번호 형식
                    if len(digits) == 10:
                        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
                    elif len(digits) == 11:
                        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                    else:
                        return digits
    
    def hyperlink_urls(self, text):
        """메시지 내용 중 URL을 하이퍼링크 형식(<a> 태그)으로 변환하는 함수입니다."""
        if not text:
            return ""
        # URL 패턴을 정규표현식으로 검색
        url_pattern = re.compile(r'((https?://|www\.)[^\s]+)')
        # 매칭된 URL을 <a href='URL'>URL</a> 형식으로 변경하는 내부 함수
        def replace(match):
            url = match.group(0)
            if url.startswith("www."):
                url = "http://" + url
            return f"<a href='{url}'>{match.group(0)}</a>"
        # 전체 텍스트에서 URL 부분을 치환하여 반환
        return url_pattern.sub(replace, text)
    
    def get_conversations(self):
        """모든 대화 상대 목록을 가져옵니다."""
        if not self.conn_message_db:
            if not self.connect_to_message_db():
                return []
        
        try:
            cursor = self.conn_message_db.cursor()
            # message 테이블과 handle 테이블을 JOIN하여 대화 상대 목록을 추출합니다.
            query = """
            SELECT DISTINCT chatId
            FROM Message
            """
            cursor.execute(query)
            conversations = []
            # 각 대화 상대에 대해 전화번호 포맷팅 적용 후 리스트에 추가
            for row in cursor.fetchall():
                conversations.append({
                    'chatId': row['chatId'],
                    'handle_id': row['chatId'],
                    'formatted_id':row['chatId'],
                })
            return conversations
        except sqlite3.Error as e:
            print(f"대화 목록 조회 오류: {e}")
            return []
    
    def get_conversation_messages(self, handle_rowid):
        """특정 채팅방의 모든 메시지를 가져옵니다."""
        if not self.conn_message_db:
            if not self.connect_to_message_db():
                return []
        
        try:
            if not self.my_id:
                self.my_id = self.get_my_id()
            
            cursor = self.conn_message_db.cursor()
            # 지정된 handle_rowid에 해당하는 메시지를 시간 순으로 조회합니다.
            query = """
            SELECT chatId, userId, sentAt, readAt, message, attachment, serverLogId
            FROM Message 
            WHERE chatId = ?
            ORDER BY sentAt ASC
            """
            cursor.execute(query, (handle_rowid,))
            messages = []
            
            for row in cursor.fetchall():
                
                # # 메시지 텍스트가 "사진"이면 첨부파일 경로를 조회 (간단 예시)
                # attachment_path = None
                # if row["text"] and row["text"].strip() == "사진":
                #     attachment_path = self.get_attachment_path(row["guid"])
                
                # 각 메시지 정보를 딕셔너리 형태로 저장
                messages.append({
                    'serverLogId': row['serverLogId'],
                    'userId': row['userId'],
                    'message': row['message'] if row['message'] else "",
                    'sentAt': KakaoTalkAnalyzer.convert_date(row['sentAt']),
                    'sentAt_string': KakaoTalkAnalyzer.format_date(KakaoTalkAnalyzer.convert_date(row['sentAt'])),
                    'is_from_me': True if row['userId'] == self.my_id else False,
                    'direction': '발신' if row['userId'] == self.my_id else '수신',
                    'attachment':  row['attachment']
                })
            
            return messages
        except sqlite3.Error as e:
            print(f"메시지 조회 오류: {e}")
            return []
    
    def get_attachment_path(self, message_guid):
        """메시지의 첨부파일 경로를 가져옵니다."""
        if not self.conn_message_db:
            if not self.connect_to_message_db():
                return None
        
        try:
            cursor = self.conn_message_db.cursor()
            # message, message_attachment_join, attachment 테이블을 JOIN하여 첨부파일의 filename을 조회합니다.
            query = """
            SELECT attachment.filename
            FROM Message
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
    
    def get_all_kakaotalk_messages(self, limit=1000):
        """모든 KakaoTalk 메시지를 가져옵니다. (최대 limit개의 메시지를 최신순으로 조회)"""
        if not self.conn_message_db:
            if not self.connect_to_message_db():
                return pd.DataFrame()
        
        try:
            query = """
            SELECT 
                id, userId, message, attachment, readAt, sentAt, prevId, chatId, serverLogId
            FROM 
                message
            ORDER BY 
                sentAt DESC
            LIMIT ?
            """
            # 쿼리 결과를 DataFrame 형태로 불러옴
            df = pd.read_sql_query(query, self.conn_message_db, params=(limit,))
            
            # 특수한 시간 형식을 일반 datetime 객체로 변환하는 함수

            
            # 날짜 컬럼 변환
            df['sentAt'] = df['sentAt'].apply(KakaoTalkAnalyzer.convert_date)

            # 발신/수신 여부에 따라 방향 컬럼 추가
            if not self.my_id:
                self.my_id = self.get_my_id()
            df['direction'] = df['userId'].apply(lambda x: '발신' if x == self.my_id else '수신')
            # # 전화번호 포맷팅을 적용한 컬럼 추가
            # df['formatted_contact'] = df['contact_id'].apply(self.format_phone_number)
            return df
        except Exception as e:
            print(f"전체 KakaoTalk 메시지 조회 오류: {e}")
            return pd.DataFrame()
    
    def get_kakaotalk_stats(self, df=None):
        """KakaoTalk 통계 정보를 계산하여 반환합니다.
        
        계산 항목:
          - total: 전체 메시지 수
          - sent: 발신 메시지 수
          - received: 수신 메시지 수
          - contacts: 고유 연락처 수
        """
        if not self.my_id:
            self.my_id = self.get_my_id()

        if df is None:
            df = self.get_all_kakaotalk_messages()
        
        if df.empty:
            return {
                'total': 0,
                'sent': 0,
                'received': 0,
                'contacts': 0
            }
        
        stats = {
            'total': len(df),
            'sent': len(df[df['userId'] == self.my_id]),
            'received': len(df[df['userId'] != self.my_id]),
            'contacts': df['chatId'].nunique()
        }
        
        return stats

    @staticmethod
    def convert_date(date_value):
        # 1970년 1월 1일 (Unix epoch)과 2001년 1월 1일 (cEpoch) 사이의 차이
        unix_epoch = datetime(1970, 1, 1)
        c_epoch = datetime(2001, 1, 1)
        delta = c_epoch - unix_epoch
        
        # date_value는 Unix timestamp (초 단위)
        timestamp = unix_epoch + timedelta(seconds=int(date_value)) + delta
        return timestamp

    @staticmethod
    def format_date(date_object):
        return date_object.strftime('%Y-%m-%d %H:%M:%S')