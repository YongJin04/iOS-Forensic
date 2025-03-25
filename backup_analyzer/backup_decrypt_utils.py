from Crypto.Cipher import AES
import plistlib
import hashlib
import os

def decrypt_backup(backup_dir, password):
    """ Decrypts an iTunes encrypted backup. """
    manifest_path = os.path.join(backup_dir, "Manifest.plist")

    if not os.path.exists(manifest_path):
        print("Manifest.plist file not found.")
        return False

    with open(manifest_path, "rb") as f:
        manifest_data = plistlib.load(f)

    if not manifest_data.get("IsEncrypted", False):
        print("The backup is not encrypted.")
        return True

    encryption_key = derive_key_from_password(password, manifest_data["Salt"])
    return decrypt_manifest_db(backup_dir, encryption_key)

def derive_key_from_password(password, salt):
    """ Generates an AES key based on the user's password and salt. """
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 10000, 32)
    return key

def decrypt_manifest_db(backup_dir, encryption_key):
    """ Decrypts Manifest.db using the AES key. """
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

    print(f"Decrypted Manifest.db saved successfully: {decrypted_db_path}")
    return True
