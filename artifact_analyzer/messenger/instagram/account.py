import os
import plistlib
import sqlite3
from datetime import datetime

def extract_instagram_account_info(plist_path):
    """
    Instagram plist 파일에서 계정 정보를 추출하여 GUI에 사용할 형태로 반환
    
    Args:
        plist_path (str): com.burbn.instagram.plist 파일 경로
    
    Returns:
        dict: 추출된 Instagram 계정 정보
    """
    try:
        #print(f"[DEBUG] plist 파일 경로: {plist_path}")
        
        # plist 파일 열기
        with open(plist_path, "rb") as f:
            plist_data = plistlib.load(f)
        
        #print(f"[DEBUG] plist 파일 로드 완료, 키 개수: {len(plist_data)}")
        #print(f"[DEBUG] plist 키 목록(처음 10개): {list(plist_data.keys())[:10]}")
        
        # GUI에 표시할 계정 정보 구조
        account_info = {
            "username": None,
            "user_id": None,
            "profile_picture_url": None,
            "last_login": None,
            "app_version": None,
            "os_version": None,
            "session_duration": None,
            "network_type": None,
            "related_accounts": [],
            "account_settings": {},
            "forensic_info": {}
        }
        
        # 사용자 ID 추출
        if "switcherLoggedInUid" in plist_data:
            account_info["user_id"] = str(plist_data["switcherLoggedInUid"])
            #print(f"[DEBUG] 사용자 ID: {account_info['user_id']}")
        else:
            print("[DEBUG] 사용자 ID를 찾을 수 없음 (switcherLoggedInUid 키 없음)")
        
        # 마지막 로그인한 계정 정보 추출
        if "last-logged-in-account-dict" in plist_data:
            login_dict = plist_data["last-logged-in-account-dict"]
            #print(f"[DEBUG] 계정 정보 딕셔너리: {login_dict}")
            account_info["username"] = login_dict.get("username")
            account_info["profile_picture_url"] = login_dict.get("profilePictureURLString")
            #print(f"[DEBUG] 사용자명: {account_info['username']}")
            #print(f"[DEBUG] 프로필 사진 URL: {account_info['profile_picture_url']}")
        else:
            print("[DEBUG] 계정 정보 딕셔너리를 찾을 수 없음 (last-logged-in-account-dict 키 없음)")
        
        # 세션 정보
        if "last_session_background_time" in plist_data:
            account_info["last_login"] = str(plist_data["last_session_background_time"])
            #print(f"[DEBUG] 마지막 로그인: {account_info['last_login']}")
        
        if "kUserDefaultActivityMonitorAppVersionKey" in plist_data:
            account_info["app_version"] = str(plist_data["kUserDefaultActivityMonitorAppVersionKey"])
            #print(f"[DEBUG] 앱 버전: {account_info['app_version']}")
        
        if "kUserDefaultActivityMonitorOsVersionKey" in plist_data:
            account_info["os_version"] = str(plist_data["kUserDefaultActivityMonitorOsVersionKey"])
            #print(f"[DEBUG] OS 버전: {account_info['os_version']}")
        
        if "last_session_duration" in plist_data:
            account_info["session_duration"] = str(plist_data["last_session_duration"])
            #print(f"[DEBUG] 세션 시간: {account_info['session_duration']}")
        
        if "last_session_network_type" in plist_data:
            account_info["network_type"] = str(plist_data["last_session_network_type"])
            #print(f"[DEBUG] 네트워크 타입: {account_info['network_type']}")
        
        # 관련 계정 정보 수집
        related_accounts = []
        #print("[DEBUG] 관련 계정 추출 시작")
        
        for key in plist_data:
            # 관련 계정 ID가 들어있는 배열 처리
            if "FbIDsKey" in key and isinstance(plist_data[key], list):
                #print(f"[DEBUG] FbIDsKey 발견: {key}, 값: {plist_data[key]}")
                for account_id in plist_data[key]:
                    if account_id and account_id != "0" and str(account_id) != account_info["user_id"]:
                        related_accounts.append({
                            "id": str(account_id),
                            "status": "연결됨"
                        })
                        #print(f"[DEBUG] 관련 계정 추가: {account_id}")
            
            # account-badges-preferences- 형식의 키 처리
            elif key.startswith("account-badges-preferences-"):
                account_id = key.replace("account-badges-preferences-", "")
                #print(f"[DEBUG] 배지 설정 계정 발견: {account_id}")
                if account_id and account_id != "0" and account_id != account_info["user_id"]:
                    related_accounts.append({
                        "id": account_id,
                        "status": "배지 설정 있음"
                    })
                    #print(f"[DEBUG] 배지 설정 계정 추가: {account_id}")
        
        # 중복 제거
        unique_accounts = {}
        for account in related_accounts:
            if account["id"] not in unique_accounts:
                unique_accounts[account["id"]] = account
        
        account_info["related_accounts"] = list(unique_accounts.values())
        #print(f"[DEBUG] 최종 관련 계정 수: {len(account_info['related_accounts'])}")
        
        # 계정 설정 정보 수집
        account_settings = {}
        settings_keys = [
            "ds-user-did-see-ds-feature",
            "user-has-logged-in-once",
            "switcher-education-account-count-key",
            "switcher-education-logged-in-account-count-key",
            "switcher-education-has-linked-account-key",
            "foa_post_login_toast_eligible"
        ]
        
        #print("[DEBUG] 계정 설정 추출 시작")
        for key in settings_keys:
            if key in plist_data:
                # 키 이름을 사용자 친화적으로 변경
                display_key = key.replace("-", " ").title().replace("Ds", "DS").replace("Foa", "FOA")
                account_settings[display_key] = str(plist_data[key])
                #print(f"[DEBUG] 계정 설정 추가: {display_key} = {account_settings[display_key]}")
        
        account_info["account_settings"] = account_settings
        
        # 포렌식 분석 정보 수집
        #print("[DEBUG] 포렌식 정보 추출 시작")
        forensic_info = {
            "Auth Token 정보": {},
            "마지막 세션 시간": None,
            "계정 인증 방식": None
        }
        
        # 인증 토큰 정보 수집
        auth_tokens = {}
        auth_token_count = 0
        for key in plist_data:
            if key.startswith("authDataStorage:"):
                auth_token_count += 1
                user_id = key.split(":")[-1]
                #print(f"[DEBUG] 인증 토큰 발견: {key}, 사용자 ID: {user_id}")
                if user_id == account_info["user_id"]:
                    auth_tokens["현재 계정"] = str(plist_data[key])
                    #print("[DEBUG] 현재 계정 토큰 저장됨")
                else:
                    auth_tokens[f"계정 {user_id}"] = str(plist_data[key])
                    #print(f"[DEBUG] 다른 계정 토큰 저장됨: {user_id}")
        
        #print(f"[DEBUG] 총 인증 토큰 수: {auth_token_count}")
        if auth_tokens:
            forensic_info["Auth Token 정보"] = auth_tokens
        
        # 마지막 세션 및 앱 접근 시간 정보
        if "last_session_background_time" in plist_data:
            try:
                bg_time = plist_data["last_session_background_time"]
                #print(f"[DEBUG] 마지막 세션 시간 원본 값: {bg_time}, 타입: {type(bg_time)}")
                if isinstance(bg_time, datetime):
                    forensic_info["마지막 세션 시간"] = bg_time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    forensic_info["마지막 세션 시간"] = str(bg_time)
                #print(f"[DEBUG] 변환된 마지막 세션 시간: {forensic_info['마지막 세션 시간']}")
            except Exception as e:
                print(f"[DEBUG] 세션 시간 변환 중 오류: {e}")
                forensic_info["마지막 세션 시간"] = str(plist_data["last_session_background_time"])
        
        # 마지막 인상 날짜 정보
        if "switcher-last-impression-date-key" in plist_data:
            try:
                impression_date = plist_data["switcher-last-impression-date-key"]
                #print(f"[DEBUG] 마지막 인상 날짜 원본 값: {impression_date}, 타입: {type(impression_date)}")
                if isinstance(impression_date, datetime):
                    forensic_info["마지막 계정 전환 시간"] = impression_date.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    forensic_info["마지막 계정 전환 시간"] = str(impression_date)
                #print(f"[DEBUG] 변환된 마지막 인상 날짜: {forensic_info['마지막 계정 전환 시간']}")
            except Exception as e:
                #print(f"[DEBUG] 인상 날짜 변환 중 오류: {e}")
                forensic_info["마지막 계정 전환 시간"] = str(plist_data["switcher-last-impression-date-key"])
        
        # 인증 방식 추정
        has_auth_token = False
        if account_info["user_id"]:
            auth_key = f"authDataStorage:{account_info['user_id']}"
            has_auth_token = any(key.startswith(auth_key) for key in plist_data)
            #print(f"[DEBUG] 인증 토큰 확인: {auth_key}, 존재 여부: {has_auth_token}")
            
        if has_auth_token:
            forensic_info["계정 인증 방식"] = "토큰 기반 인증"
            
            #print("[DEBUG] 인증 방식: 토큰 기반 인증")
        
        account_info["forensic_info"] = forensic_info
        
        #print("[DEBUG] 계정 정보 추출 완료")
        return account_info
    
    except Exception as e:
        print(f"[ERROR] 계정 정보 추출 중 오류 발생: {e}")
        import traceback
        print(traceback.format_exc())
        return {}

def find_instagram_plist(backup_path=None):
    """
    백업 경로에서 Instagram plist 파일을 찾는 함수
    
    Args:
        backup_path (str): iOS 백업 디렉토리 경로
    
    Returns:
        str: plist 파일 경로 또는 None
    """
    print(f"[DEBUG] Instagram plist 파일 검색 시작, 경로: {backup_path}")
    
    # # 백업 경로가 제공되지 않았거나 현재 디렉토리에서 파일을 찾을 경우
    # if not backup_path:
    #     # 먼저 현재 디렉토리에서 찾기
    #     if os.path.exists("com.burbn.instagram.plist"):
    #         print("[DEBUG] 현재 디렉토리에서 plist 파일 발견")
    #         return "com.burbn.instagram.plist"
        
    #     # instagram 폴더가 있으면 그 안에서 찾기
    #     if os.path.exists("instagram/com.burbn.instagram.plist"):
    #         print("[DEBUG] instagram 폴더에서 plist 파일 발견")
    #         return "instagram/com.burbn.instagram.plist"
        
    #     print("[DEBUG] 현재 디렉토리에서 plist 파일을 찾을 수 없음")
    #     return None
    
    # iOS 백업에서 찾기
    manifest_db_path = os.path.join(backup_path, "Manifest.db")
    #print(f"[DEBUG] Manifest.db 경로 확인: {manifest_db_path}")
    
    if not os.path.exists(manifest_db_path):
        print(f"[ERROR] {manifest_db_path}를 찾을 수 없습니다.")
        return None

    try:
        print("[DEBUG] Manifest.db 연결 시도")
        conn = sqlite3.connect(manifest_db_path)
        cursor = conn.cursor()

        query = """
            SELECT fileID, relativePath
            FROM Files
            WHERE relativePath = 'com.burbn.instagram.plist'
            OR relativePath LIKE '%/com.burbn.instagram.plist';
        """
        #print(f"[DEBUG] 실행할 쿼리: {query}")

        cursor.execute(query)
        result = cursor.fetchone()
        #print(f"[DEBUG] 쿼리 결과: {result}")
        
        conn.close()

        if result:
            file_id, relative_path = result
            #print(f"[DEBUG] 파일 ID: {file_id}, 상대 경로: {relative_path}")
            
            hashed_file_path = os.path.join(backup_path, file_id[:2], file_id)
            
            #print(f"[DEBUG] 해시된 파일 경로: {hashed_file_path}")
            
            if os.path.exists(hashed_file_path):
                #print(f"[DEBUG] 발견된 Instagram plist 파일: {relative_path}")
                return hashed_file_path
            else:
                print(f"[DEBUG] 해시된 파일이 존재하지 않음: {hashed_file_path}")
    except Exception as e:
        print(f"[ERROR] Manifest.db 검색 중 오류: {e}")
        import traceback
        print(traceback.format_exc())
    
    print("[DEBUG] Instagram plist 파일을 찾을 수 없음")
    return None

def get_instagram_account_info(backup_path=None):
    """
    Instagram 계정 정보를 가져와 GUI에 표시할 수 있는 형태로 반환
    
    Args:
        backup_path (str): iOS 백업 디렉토리 경로
        
    Returns:
        dict: GUI에 표시할 계정 정보
    """
    try:
        #print(f"[DEBUG] Instagram 계정 정보 추출 시작, 백업 경로: {backup_path}")
        
        # plist 파일 찾기
        plist_path = find_instagram_plist(backup_path)
        
        if not plist_path:
            print("[INFO] Instagram plist 파일을 찾을 수 없습니다.")
            return {}
        
        
        #print(f"[DEBUG] plist 파일 찾음: {plist_path}")
        
        # 계정 정보 추출
        account_info = extract_instagram_account_info(plist_path)
        #print(f"[DEBUG] 추출된 계정 정보 개요: {', '.join([f'{k}: {type(v)}' for k, v in account_info.items()])}")
        
        return account_info
    
    except Exception as e:
        print(f"[ERROR] Instagram 계정 정보 추출 중 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return {}