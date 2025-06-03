import os
import sqlite3
import datetime
from backup_analyzer.backuphelper import BackupPathHelper

def find_safari_history(backup_path=None):
    """
    Safari 방문 기록 데이터베이스 (History.db) 파일 경로 찾기
    """
    
    if not backup_path or not os.path.exists(backup_path):
        print(f"[ERROR] 유효한 백업 경로가 필요합니다: {backup_path}")
        return None
    
    # BackupPathHelper 클래스 활용
    helper = BackupPathHelper(backup_path)
    
    # Instagram plist 파일 검색
    search_results = helper.find_files_by_keyword("Safari/History.db")
    
    if not search_results:
        print("[DEBUG] safari/history.db  파일을 찾을 수 없음")
        return None
    
    # 전체 경로 가져오기
    full_paths = helper.get_full_paths(search_results)
    
    if full_paths:
        full_path, relative_path = full_paths[0]  # 첫 번째 결과 사용
        return full_path
    else:
        print("[DEBUG] safari/history.db 파일을 찾을 수 없음")
        return None

def get_safari_history(backup_path=None):
    db_path = find_safari_history(backup_path)
    if not db_path:
        return "Safari 기록 데이터베이스를 찾을 수 없습니다."
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""SELECT url, title, visit_time
                        FROM history_visits
                        JOIN history_items ON history_visits.history_item = history_items.id
                        ORDER BY visit_time DESC;""")
        
        history = []
        for row in cursor.fetchall():
            url = row[0]
            title = row[1]
            timestamp = row[2]
            visit_time = datetime.datetime(2001, 1, 1) + datetime.timedelta(seconds=timestamp)
            formatted_time = visit_time.strftime('%Y-%m-%d %H:%M:%S')
            history.append((title, url, formatted_time))
        
        conn.close()
        return history if history else "기록이 없습니다."
    except Exception as e:
        return f"오류 발생: {e}"


