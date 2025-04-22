import os

_SQLITE_MAGIC_HEX = "53514c69746520666f726d6174203300"  # SQLite 파일의 File Signature

def is_backup_encrypted(backup_path: str) -> bool:
    manifest_db = os.path.join(backup_path, "Manifest.db")
    try:
        with open(manifest_db, "rb") as fp:
            header = fp.read(16)
            return header.hex() != _SQLITE_MAGIC_HEX
    except FileNotFoundError:
        # 파일 자체가 없으면 처리 불가 → 암호화된 것으로 간주
        return True

def decrypt_backup(*_args, **_kwargs) -> bool:
    return False
