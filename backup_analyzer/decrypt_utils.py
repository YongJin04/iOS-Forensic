import os
import plistlib
from Crypto.Cipher import AES
import hashlib

def decrypt_backup(backup_dir, password):
    """
    iTunes 암호화된 백업을 복호화하는 함수
    """
    manifest_path = os.path.join(backup_dir, "Manifest.plist")

    if not os.path.exists(manifest_path):
        print("Manifest.plist 파일을 찾을 수 없습니다.")
        return False

    with open(manifest_path, "rb") as f:
        manifest_data = plistlib.load(f)

    if not manifest_data.get("IsEncrypted", False):
        print("백업이 암호화되지 않았습니다.")
        return True

    encryption_key = derive_key_from_password(password, manifest_data["Salt"])
    return decrypt_manifest_db(backup_dir, encryption_key)

def derive_key_from_password(password, salt):
    """
    사용자의 비밀번호와 Salt를 기반으로 AES 키를 생성하는 함수
    """
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 10000, 32)
    return key

def decrypt_manifest_db(backup_dir, encryption_key):
    """
    AES 키를 사용하여 Manifest.db 복호화
    """
    manifest_db_path = os.path.join(backup_dir, "Manifest.db")

    with open(manifest_db_path, "rb") as f:
        encrypted_data = f.read()

    iv = encrypted_data[:16]
    cipher = AES.new(encryption_key, AES.MODE_CBC, iv)
    
    decrypted_data = cipher.decrypt(encrypted_data[16:])
    decrypted_data = decrypted_data.rstrip(b"\x00")

    decrypted_db_path = os.path.join(backup_dir, "Manifest_decrypted.db")
    with open(decrypted_db_path, "wb") as f:
        f.write(decrypted_data)

    print(f"복호화된 Manifest.db 저장 완료: {decrypted_db_path}")
    return True
