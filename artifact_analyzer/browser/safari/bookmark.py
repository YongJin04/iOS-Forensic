import os
import sqlite3
from backup_analyzer.backuphelper import BackupPathHelper

def find_safari_bookmarks(backup_path=None):
    """
    Safari 북마크 데이터베이스 (Bookmarks.db) 파일 경로 찾기
    """
    
    if not backup_path or not os.path.exists(backup_path):
        print(f"[ERROR] 유효한 백업 경로가 필요합니다: {backup_path}")
        return None
    
    # BackupPathHelper 클래스 활용
    helper = BackupPathHelper(backup_path)
    
    # Instagram plist 파일 검색
    search_results = helper.find_files_by_keyword("Safari/Bookmarks.db")
    
    if not search_results:
        print("[DEBUG] Instagram plist 파일을 찾을 수 없음")
        return None
    
    # 전체 경로 가져오기
    full_paths = helper.get_full_paths(search_results)
    
    if full_paths:
        full_path, relative_path = full_paths[0]  # 첫 번째 결과 사용
        print(f"[DEBUG] 발견된 Instagram plist 파일: {relative_path}")
        return full_path
    else:
        print("[DEBUG] Instagram plist 파일을 찾을 수 없음")
        return None




def get_safari_bookmarks(backup_path=None):
    """
    Safari 북마크 정보를 조회하여 반환

    :param backup_path: 백업 파일 경로
    :return: 북마크 리스트 [(제목, URL)] 또는 오류 메시지
    """
    db_path = find_safari_bookmarks(backup_path)
    if not db_path:
        return "Safari 북마크 데이터베이스를 찾을 수 없습니다."
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
                        WITH RECURSIVE FolderHierarchy AS (
                            -- 1. 최상위(root) 폴더 선택 (parent가 NULL인 경우)
                            SELECT id, title AS folder, parent
                            FROM bookmarks
                            WHERE parent IS NULL

                            UNION ALL

                            -- 2. 재귀적으로 하위 폴더를 찾아 연결
                            SELECT b.id, fh.folder || ' / ' || b.title, b.parent
                            FROM bookmarks b
                            JOIN FolderHierarchy fh ON b.parent = fh.id
                        )
                        SELECT fh.folder, b.title AS bookmark_title, b.url
                        FROM FolderHierarchy fh
                        JOIN bookmarks b ON fh.id = b.parent
                        WHERE b.url IS NOT NULL
                        ORDER BY fh.folder, b.title;

        """)
        
        bookmarks = []
        for row in cursor.fetchall():
            folder = row[0] if row[0] else "제목 없음"
            title = row[1]
            url = row[2]
            bookmarks.append((folder,title, url))
        
        conn.close()
        return bookmarks if bookmarks else "저장된 북마크가 없습니다."
    
    except sqlite3.Error as e:
        return f"SQLite 오류 발생: {e}"
    except Exception as e:
        return f"오류 발생: {e}"
