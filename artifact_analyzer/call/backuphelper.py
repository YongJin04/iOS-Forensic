import os
import sqlite3
import hashlib

class BackupPathHelper:
    """iOS 백업 파일 경로를 찾는 도우미 클래스"""
    
    def __init__(self, backup_path):
        self.backup_path = backup_path
        
    def get_file_path_from_manifest(self, relative_path):
        """
        Manifest.db 파일에서 상대 경로에 해당하는 해시 파일명을 찾아 전체 경로 반환
        """
        manifest_path = os.path.join(self.backup_path, "Manifest.db")
        if not os.path.exists(manifest_path):
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
                # 해시 파일명을 이용해 전체 경로 반환
                return os.path.join(self.backup_path, result[0][:2], result[0])
                
        except Exception as e:
            print(f"Manifest.db 검색 오류: {str(e)}")
            
        return None

