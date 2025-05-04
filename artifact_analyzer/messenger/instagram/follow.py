import os
import plistlib
from plistlib import UID
import unicodedata  # 유니코드 정규화를 위한 모듈 추가
import sqlite3


def normalize_text(text):
    """
    NFD 방식으로 저장된 한글 문자열을 NFC 방식으로 정규화
    """
    if text is None:
        return None
    
    if isinstance(text, str):
        return unicodedata.normalize('NFC', text)
    return text


def extract_value(objects, uid_or_value):
    """UID이면 실제 값을 반환하고, 아니면 값 그대로 반환"""
    if isinstance(uid_or_value, UID):
        value = objects[uid_or_value.data]
        # 문자열 값에 대해 정규화 적용
        if isinstance(value, str):
            return normalize_text(value)
        return value
    
    # UID가 아닌 경우에도 문자열이면 정규화 적용
    if isinstance(uid_or_value, str):
        return normalize_text(uid_or_value)
    return uid_or_value


def find_instagram_following_file(backup_path):
    manifest_db_path = os.path.join(backup_path, "Manifest.db")
    if not os.path.exists(manifest_db_path):
        print("[ERROR] Manifest.db를 찾을 수 없습니다.")
        return None

    conn = sqlite3.connect(manifest_db_path)
    cursor = conn.cursor()

    query = """
    SELECT fileID, relativePath
    FROM Files
    WHERE relativePath LIKE '%user_bootstrap/shared_bootstraps.plist';
    """
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()

    if result:
        file_id, relative_path = result
        hashed_file_path = os.path.join(backup_path, file_id[:2], file_id)
        #print(f"[DEBUG] 발견된 plist 상대경로: {normalize_text(relative_path)}")
        #print(f"[DEBUG] 실제 파일 경로: {hashed_file_path}")
        return hashed_file_path
    else:
        print("[DEBUG] Manifest.db에서 파일을 찾지 못했습니다.")
        return None


def extract_user_info(obj, objects):
    """객체에서 사용자 정보 추출"""
    user_info = {}
    
    # 객체가 UID인 경우 실제 값 가져오기
    if isinstance(obj, UID):
        obj = objects[obj.data]
    
    # 객체가 딕셔너리가 아니면 처리 불가
    if not isinstance(obj, dict):
        return None
    
    # 가능한 사용자 정보 키
    possible_keys = {
        'user_id': ['user_id', 'userId', 'id', 'pk'],
        'username': ['username', 'user_name', 'userName', 'login'],
        'full_name': ['fullname', 'full_name', 'fullName', 'name', 'display_name'],
        'profile_url': ['profile_url', 'profileUrl', 'profile_pic_url', 'profilePicUrl', 'profile_pic'],
        'followed_by': ['followed_by', 'followedBy', 'is_followed_by', 'isFollowedBy']
    }
    
    # 각 타입의 키를 찾아서 정보 추출
    for info_key, possible_key_list in possible_keys.items():
        for key in possible_key_list:
            if key in obj:
                value = extract_value(objects, obj[key])
                user_info[info_key] = value
                break
    
    # extra_attributes 검사
    for key in ['extra_attributes', 'extraAttributes', 'attributes']:
        if key in obj:
            extra_attrs = extract_value(objects, obj[key])
            if isinstance(extra_attrs, dict):
                # followed_by 추가 확인
                for fb_key in possible_keys['followed_by']:
                    if fb_key in extra_attrs:
                        user_info['followed_by'] = extract_value(objects, extra_attrs[fb_key])
                        break
    
    # followed_by가 없으면 기본값으로 False 설정
    if 'followed_by' not in user_info:
        user_info['followed_by'] = False
    
    # 모든 문자열 값에 대해 정규화 적용
    for key, value in user_info.items():
        if isinstance(value, str):
            user_info[key] = normalize_text(value)
    
    return user_info


def find_user_patterns(objects):
    """사용자 정보 패턴 찾기"""
    user_info_objects = []
    
    # 사용자 정보를 식별할 수 있는 키워드
    username_keywords = ["username", "user_name", "userName"]
    user_id_keywords = ["user_id", "userId", "id", "pk"]
    profile_keywords = ["profile", "profile_url", "profileUrl", "profile_pic", "profile_pic_url"]
    name_keywords = ["fullname", "full_name", "fullName", "name", "display_name"]
    
    # 모든 객체 중에서 딕셔너리 찾기
    for i, obj in enumerate(objects):
        if isinstance(obj, dict):
            # 사용자 관련 키가 있는지 확인
            has_username = any(key in obj for key in username_keywords)
            has_user_id = any(key in obj for key in user_id_keywords)
            has_profile = any(key in obj for key in profile_keywords)
            has_name = any(key in obj for key in name_keywords)
            
            # 사용자 정보로 의심되는 객체라면 저장
            if (has_username or has_user_id) and (has_profile or has_name):
                user_info = extract_user_info(obj, objects)
                if user_info and 'username' in user_info and 'user_id' in user_info:
                    user_info_objects.append(user_info)
    
    return user_info_objects


def process_following_data(file_path):
    """shared_bootstraps.plist 파일에서 팔로잉 정보 추출"""
    try:
        with open(file_path, "rb") as f:
            plist = plistlib.load(f)
        
        # 기본 구조 파싱
        objects = plist.get("$objects", [])
        top = plist.get("$top", {})
        
        # 사용자 정보 목록
        following_users = []
        
        # root 객체 확인
        if 'root' in top:
            root_uid = top['root'].data
            root_obj = objects[root_uid]
            
            # users 키가 있는지 확인
            if isinstance(root_obj, dict) and 'users' in root_obj:
                users_uid = root_obj['users']
                users_array = extract_value(objects, users_uid)
                
                if isinstance(users_array, list):
                    for user_uid in users_array:
                        user_info = extract_user_info(user_uid, objects)
                        if user_info and 'username' in user_info and 'user_id' in user_info:
                            following_users.append(user_info)
        
        # 사용자 정보가 없으면 전체 객체에서 패턴 검색
        if not following_users:
            following_users = find_user_patterns(objects)
        
        # 필수 필드 검사 및 누락된 필드 처리
        for user in following_users:
            # 필수 필드가 없으면 기본값 설정
            if 'user_id' not in user:
                user['user_id'] = ""
            if 'username' not in user:
                user['username'] = normalize_text("알 수 없음")
            if 'full_name' not in user:
                user['full_name'] = ""
            if 'profile_url' not in user or not user['profile_url']:
                user['profile_url'] = ""
            if 'followed_by' not in user:
                user['followed_by'] = False
        
        return following_users
        
    except Exception as e:
        print(f"오류 발생: {e}")
        return []


def get_instagram_following(backup_path=None):
    """
    Instagram 팔로잉 정보 분석 및 데이터 반환
    """
    # 파일 경로 찾기
    file_path = find_instagram_following_file(backup_path)
    
    if not file_path:
        # 파일을 찾지 못한 경우 빈 리스트 반환
        return []
    
    # 파일에서 데이터 추출
    following_data = process_following_data(file_path)
    return following_data