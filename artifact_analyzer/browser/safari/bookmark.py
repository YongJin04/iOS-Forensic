import os
import sqlite3
from artifact_analyzer.call.backuphelper import BackupPathHelper

def find_safari_bookmarks(backup_path=None):
    """
    Safari 북마크 데이터베이스 (Bookmarks.db) 파일 경로 찾기
    """
    if backup_path:
        backup_helper = BackupPathHelper(backup_path)
        bookmark_paths = [
            "Library/Safari/Bookmarks.db",
            "private/var/mobile/Library/Safari/Bookmarks.db",
            "HomeDomain/Library/Safari/Bookmarks.db"
        ]

        # 1. Manifest.db에서 찾기
        for path in bookmark_paths:
            file_path = backup_helper.get_file_path_from_manifest(path)
            if file_path and os.path.exists(file_path):
                return file_path
        
    
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
