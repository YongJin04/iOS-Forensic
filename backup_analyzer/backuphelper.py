import os
import sqlite3

class BackupPathHelper:
    """iOS 백업 파일 경로를 찾는 도우미 클래스"""
    
    def __init__(self, backup_path):
        self.backup_path = backup_path
        
    def find_files_by_keyword(self, keyword, file_type=None):
            """
            키워드를 포함하는 파일을 찾는 메서드
            
            Args:
                keyword (str): 검색할 키워드
                file_type (str, optional): 파일 유형 (예: '.plist', '.db'). None이면 모든 파일 검색.
            
            Returns:
                list: (fileID, relativePath) 튜플의 리스트
            """
            manifest_path = os.path.join(self.backup_path, "Manifest.db")
            if not os.path.exists(manifest_path):
                print(f"[ERROR] Manifest.db를 찾을 수 없습니다: {manifest_path}")
                return []
                
            try:
                conn = sqlite3.connect(manifest_path)
                cursor = conn.cursor()
                
                # SQL 쿼리 구성
                if file_type:
                    query = f"""
                    SELECT fileID, relativePath
                    FROM Files
                    WHERE relativePath LIKE '%{keyword}%' AND relativePath LIKE '%{file_type}';
                    """
                else:
                    query = f"""
                    SELECT fileID, relativePath
                    FROM Files
                    WHERE relativePath LIKE '%{keyword}%';
                    """
                    
                print(f"[DEBUG] SQL 쿼리 실행: {query.strip()}")
                cursor.execute(query)
                results = cursor.fetchall()
                conn.close()
                
                if results:
                    print(f"[INFO] '{keyword}' 키워드로 {len(results)}개 파일을 찾았습니다.")
                    return results
                else:
                    print(f"[INFO] '{keyword}' 키워드로 파일을 찾지 못했습니다.")
                    return []
                    
            except Exception as e:
                print(f"[ERROR] SQL 쿼리 실행 중 오류: {str(e)}")
                return []
        
    def get_full_paths(self, search_results):
        """
        검색 결과에서 전체 파일 경로 목록을 반환
        
        Args:
            search_results (list): (fileID, relativePath) 튜플의 리스트
            
        Returns:
            list: (full_path, relative_path) 튜플의 리스트
        """
        full_paths = []
        for file_id, relative_path in search_results:
            full_path = os.path.join(self.backup_path, file_id[:2], file_id)
            if os.path.exists(full_path):
                full_paths.append((full_path, relative_path))
            else:
                print(f"[WARNING] 파일이 존재하지 않습니다: {full_path}")
        
        return full_paths