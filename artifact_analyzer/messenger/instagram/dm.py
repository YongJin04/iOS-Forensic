import sqlite3
import os
from biplist import readPlistFromString
import datetime
import pytz
import unicodedata  # 유니코드 정규화를 위한 모듈 추가
from collections import defaultdict
from backup_analyzer.backuphelper import BackupPathHelper

class InstagramDMAnalyzer:
    """Instagram DM 분석을 위한 클래스"""
    
    def __init__(self, backup_path=None):
        """
        Instagram DM 분석기 초기화
        
        Parameters:
        - backup_path: iOS 백업 경로
        """
        self.backup_path = backup_path
        self.db_paths = []
        self.db_original_names = {}  # 해시된 경로와 원본 파일명 매핑 저장
        
        if self.backup_path:
            self.find_instagram_dbs()
    
    def find_instagram_dbs(self):
        """백업 경로에서 Instagram DB 파일들을 찾음"""
        if not self.backup_path or not os.path.exists(self.backup_path):
            print(f"[ERROR] 유효한 백업 경로가 필요합니다: {self.backup_path}")
            return
            
        # BackupPathHelper 클래스 활용
        try:
            helper = BackupPathHelper(self.backup_path)
        except Exception as e:
            print(f"[ERROR] BackupPathHelper 초기화 실패: {e}")
            return
        
        # DirectSQLiteDatabase 키워드로 파일 검색
        search_results = helper.find_files_by_keyword("DirectSQLiteDatabase")
        
        if not search_results:
            print("[WARNING] DirectSQLiteDatabase 관련 파일을 찾을 수 없음")
            return
        
        # DirectSQLiteDatabase 경로를 포함하는 파일들 중에서 DB 파일만 필터링
        db_files = []
        
        # get_full_paths 메서드는 (fileID, relativePath) 튜플 리스트를 받음
        try:
            full_paths = helper.get_full_paths(search_results)
            
            for full_path, relative_path in full_paths:
                # DB 파일인지 확인 (.db, .sqlite, .sqlite3 확장자)
                if any(relative_path.lower().endswith(ext) for ext in ['.db', '.sqlite', '.sqlite3']):
                    # 파일이 실제로 존재하는지 확인
                    if os.path.exists(full_path):
                        # 원본 파일명 추출 (relativePath에서 마지막 부분)
                        original_filename = os.path.basename(relative_path)
                        
                        # 원본 파일명 매핑 저장
                        self.db_original_names[full_path] = original_filename
                        db_files.append(full_path)
                    else:
                        print(f"[WARNING] 파일이 존재하지 않음: {full_path}")
        
        except Exception as e:
            print(f"[ERROR] 파일 경로 처리 중 오류: {e}")
            import traceback
            traceback.print_exc()
        
        if db_files:
            self.db_paths = db_files
            print(f"[INFO] {len(db_files)}개의 Instagram DB 파일을 찾았습니다.")
        else:
            print("[WARNING] DirectSQLiteDatabase 관련 DB 파일을 찾을 수 없음")
    
    def normalize_text(self, text):
        """
        한글 텍스트 정규화 함수 (NFD -> NFC)
        NFD로 저장된 한글을 NFC 형식으로 변환하여 올바르게 표시
        
        Parameters:
        - text: 정규화할 텍스트
        
        Returns:
        - 정규화된 텍스트
        """
        if not text:
            return text
        
        # 일관된 표시를 위해 NFC 형식으로 정규화
        return unicodedata.normalize('NFC', text)
    
    def parse_bplist_from_blob(self, blob):
        """바이너리 plist 데이터 파싱"""
        try:
            plist = readPlistFromString(blob)
            objects = plist.get("$objects", [])

            # 시간 추출
            def get_timestamp():
                for obj in objects:
                    if isinstance(obj, dict) and "NS.time" in obj:
                        apple_epoch = datetime.datetime(2001, 1, 1, tzinfo=datetime.timezone.utc)
                        utc_time = apple_epoch + datetime.timedelta(seconds=obj["NS.time"])
                        kst = pytz.timezone("Asia/Seoul")
                        return utc_time.astimezone(kst)
                return None

            timestamp = get_timestamp()
            message_id = objects[5] if len(objects) > 5 else "N/A"
            thread_id = objects[7] if len(objects) > 7 else "N/A"
            user_id = objects[8] if len(objects) > 8 else "N/A"

            # 메시지 본문 후보
            message_candidates = []
            for i in [11, 12, 14]:
                if len(objects) > i and isinstance(objects[i], str):
                    # 텍스트 정규화 적용
                    normalized_text = self.normalize_text(objects[i])
                    message_candidates.append(normalized_text)
            
            # 메시지 텍스트 정규화
            message_text = " / ".join(message_candidates) if message_candidates else "없음"
            message_text = self.normalize_text(message_text)

            # GUI에 표시할 형식으로 시간 변환
            time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "시간 정보 없음"

            return {
                "timestamp": timestamp,
                "message_id": message_id,
                "thread_id": thread_id,
                "user_id": user_id,
                "text": message_text,
                "time_str": time_str
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_chat_list(self):
        """
        Instagram DM 채팅방 목록과 메시지 가져오기
        
        Returns:
        - 모든 메시지의 통합 리스트 [{'채팅방': 방이름, '시간': 시간, '사용자': 사용자이름, '문자내용': 메시지, 'db_name': 원본DB파일명}, ...]
        """
        all_messages = []  # 모든 DB의 메시지를 하나의 리스트로 통합
        
        if not self.db_paths:
            print(f"[ERROR] DM 데이터베이스를 찾을 수 없습니다.")
            return all_messages
        
        # 모든 DB 파일에 대해 처리
        for db_path in self.db_paths:
            # 원본 파일명 사용 (없으면 해시된 파일명 사용)
            db_name = self.db_original_names.get(db_path, os.path.basename(db_path))
            
            try:
                # 데이터베이스 연결
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 테이블 구조 확인
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                # messages 테이블이 있는지 확인
                if ('messages',) not in tables:
                    print(f"[WARNING] {db_name}에 messages 테이블이 없음")
                    conn.close()
                    continue
                
                # archive 컬럼이 있는지 확인
                cursor.execute("PRAGMA table_info(messages);")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if 'archive' not in column_names:
                    print(f"[WARNING] {db_name}의 messages 테이블에 archive 컬럼이 없음")
                    conn.close()
                    continue
                
                # archive가 존재하는 행 조회
                cursor.execute("SELECT COUNT(*) FROM messages WHERE archive IS NOT NULL")
                archive_count = cursor.fetchone()[0]
                
                if archive_count == 0:
                    print(f"[INFO] {db_name}에 archive 데이터가 없음")
                    conn.close()
                    continue
                
                cursor.execute("SELECT archive FROM messages WHERE archive IS NOT NULL")
                rows = cursor.fetchall()
                
                # 채팅방별 메시지 정리
                chat_data = defaultdict(list)
                parse_success = 0
                parse_error = 0
                
                for row in rows:
                    blob = row[0]
                    parsed = self.parse_bplist_from_blob(blob)
                    if parsed and "thread_id" in parsed and "error" not in parsed:
                        chat_data[parsed["thread_id"]].append(parsed)
                        parse_success += 1
                    else:
                        parse_error += 1
                
                if parse_error > 0:
                    print(f"[WARNING] {db_name}: 파싱 실패 {parse_error}개")
                
                # 현재 DB의 데이터를 처리
                for thread_id, messages in chat_data.items():
                    # 시간순 정렬
                    sorted_messages = sorted(messages, key=lambda x: x["timestamp"] or datetime.datetime.min.replace(tzinfo=pytz.UTC))
                    
                    for msg in sorted_messages:
                        # 채팅방 이름 정규화
                        chat_name = self.normalize_text(f"채팅방 {thread_id}")
                        # 사용자 이름 정규화
                        user_name = self.normalize_text(f"사용자 {msg['user_id']}")
                        
                        # 통합 메시지 리스트에 추가
                        message_data = {
                            '채팅방': chat_name,
                            '시간': msg['time_str'],
                            '사용자': user_name,
                            '문자내용': msg['text'],  # 이미 정규화된 텍스트
                            'db_name': db_name  # 원본 파일명 사용
                        }
                        all_messages.append(message_data)
                
                conn.close()
                
            except Exception as e:
                print(f"[ERROR] 데이터베이스 처리 오류 ({db_name}): {str(e)}")
                import traceback
                traceback.print_exc()
        
        if all_messages:
            print(f"[INFO] 총 {len(all_messages)}개 메시지 추출 완료")
        else:
            print(f"[WARNING] 추출된 메시지가 없습니다")
            
        return all_messages
    
    
    
    def get_db_paths(self):
        """
        찾은 Instagram DB 파일의 원본 파일명 반환
        
        Returns:
        - 원본 DB 파일명 리스트
        """
        # 해시된 경로에서 원본 파일명으로 변환하여 반환
        original_names = []
        for db_path in self.db_paths:
            original_name = self.db_original_names.get(db_path, os.path.basename(db_path))
            original_names.append(original_name)
        
        return original_names
    
    def get_db_hash_paths(self):
        """
        찾은 Instagram DB 파일의 해시된 전체 경로 반환
        
        Returns:
        - 해시된 DB 파일 경로 리스트
        """
        return self.db_paths
    
    def get_db_original_names(self):
        """
        DB 파일의 원본 파일명 매핑 반환
        
        Returns:
        - 해시된 경로와 원본 파일명 매핑 딕셔너리
        """
        return self.db_original_names