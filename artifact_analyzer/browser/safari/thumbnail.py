import os
import io
from PIL import Image, ImageTk
from backup_analyzer.backuphelper import BackupPathHelper

def find_safari_thumbnails(backup_path):
    """
    Safari 썸네일 파일들의 전체 경로 목록을 반환
    
    Args:
        backup_path: 백업 파일 경로
        
    Returns:
        Safari 썸네일 파일들의 전체 경로 리스트 또는 빈 리스트
    """
    print(f"[DEBUG] Safari 썸네일 파일 검색 시작, 경로: {backup_path}")
    
    if not backup_path or not os.path.exists(backup_path):
        print(f"[ERROR] 유효한 백업 경로가 필요합니다: {backup_path}")
        return []
    
    # BackupPathHelper 클래스 활용
    helper = BackupPathHelper(backup_path)
    
    # Safari 썸네일 파일 검색
    print("[DEBUG] SQL 쿼리 실행: SELECT fileID, relativePath\n                    FROM Files\n                    WHERE relativePath LIKE '%Safari/Thumbnails/%%';")
    search_results = helper.find_files_by_keyword("Safari/Thumbnails/%")
    
    if not search_results:
        print("[DEBUG] Safari 썸네일 파일을 찾을 수 없음")
        return []
    
    print(f"[INFO] 'Safari/Thumbnails/%' 키워드로 {len(search_results)}개 파일을 찾았습니다.")
    
    # 전체 경로 리스트 가져오기
    full_paths = helper.get_full_paths(search_results)
    
    # 전체 경로만 추출하여 리스트로 반환
    thumbnail_paths = [full_path for full_path, relative_path in full_paths]
    
    for i, (full_path, relative_path) in enumerate(full_paths[:5]):  # 처음 5개만 로그 출력
        print(f"[DEBUG] 발견된 Safari 썸네일 파일 {i+1}: {relative_path}")
    
    if len(full_paths) > 5:
        print(f"[DEBUG] ... 외 {len(full_paths) - 5}개 파일")
        
    return thumbnail_paths

def get_safari_thumbnails(backup_path=None, max_thumbnails=50):
    """
    Safari 브라우저의 썸네일 이미지 로드

    Args:
        backup_path: 백업 파일 경로
        max_thumbnails: 최대 썸네일 개수 (기본 50개)

    Returns:
        썸네일 정보 목록 - 각 항목은 (파일명, 이미지 데이터, 이미지 크기) 형식
        또는 오류 메시지 (문자열)
    """
    try:
        thumbnails = []
        image_files = find_safari_thumbnails(backup_path)

        if not image_files:
            return "Safari 썸네일 이미지를 찾을 수 없습니다."

        # 파일 수정 시간 기준으로 정렬 (최신순)
        try:
            image_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        except Exception as sort_err:
            print(f"[WARNING] 파일 정렬 오류: {sort_err}")

        # 지정된 개수만큼 썸네일 정보 수집
        for img_path in image_files[:max_thumbnails]:
            try:
                with Image.open(img_path) as img:
                    # 원본 이미지 크기 저장
                    original_size = img.size

                    # GUI 표시용 작은 썸네일 생성 
                    img.thumbnail((200, 350), Image.LANCZOS)

                    # 이미지 데이터를 바이트로 변환
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format=img.format if img.format else 'PNG')
                    img_data = img_byte_arr.getvalue()

                    # 파일명 추출
                    file_name = os.path.basename(img_path)

                    # 썸네일 정보 추가 (파일명, 이미지 데이터, 원본 크기)
                    thumbnails.append((file_name, img_data, original_size))
                    print(f"[DEBUG] 썸네일 로드 성공: {file_name}")
            except Exception as e:
                print(f"[ERROR] 썸네일 처리 오류 ({img_path}): {str(e)}")
                continue

        if not thumbnails:
            return "Safari 썸네일 이미지가 없습니다."

        print(f"[INFO] 총 {len(thumbnails)}개의 Safari 썸네일을 로드했습니다.")
        return thumbnails

    except Exception as e:
        error_msg = f"Safari 썸네일 로드 중 오류 발생: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return error_msg


def get_thumbnail_image(thumb_data):
    """
    썸네일 데이터를 Tkinter PhotoImage로 변환

    Args:
        thumb_data: (파일명, 이미지 바이트 데이터, 원본 크기) 형식의 튜플

    Returns:
        (ImageTk.PhotoImage, 파일명, 원본 크기) 형식의 튜플
    """
    try:
        file_name, img_data, original_size = thumb_data
        image = Image.open(io.BytesIO(img_data))
        photo_image = ImageTk.PhotoImage(image)
        return (photo_image, file_name, original_size)
    except Exception as e:
        print(f"[ERROR] 이미지 변환 오류: {str(e)}")
        return None


def get_thumbnail_details(thumb_data):
    """
    썸네일의 세부 정보 추출

    Args:
        thumb_data: (파일명, 이미지 바이트 데이터, 원본 크기) 형식의 튜플

    Returns:
        {
            'file_name': 파일명,
            'original_width': 원본 너비,
            'original_height': 원본 높이,
            'file_size': 파일 크기(KB)
        }
    """
    file_name, img_data, original_size = thumb_data
    return {
        'file_name': file_name,
        'original_width': original_size[0],
        'original_height': original_size[1],
        'file_size': round(len(img_data) / 1024, 1)  # KB 단위
    }