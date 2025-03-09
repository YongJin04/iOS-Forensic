import os
import plistlib
import sqlite3

def load_manifest_plist(backup_dir: str) -> dict:
    """Manifest.plist 파일을 로드하는 함수"""
    path = os.path.join(backup_dir, "Manifest.plist")
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as f:
        return plistlib.load(f)

def load_manifest_db(backup_dir: str):
    """Manifest.db 파일에서 파일 목록을 로드하는 함수"""
    db_path = os.path.join(backup_dir, "Manifest.db")
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT fileID, domain, relativePath, flags FROM Files")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []
    conn.close()

    return [(fileID, domain, rel_path, flags) for fileID, domain, rel_path, flags in rows]
