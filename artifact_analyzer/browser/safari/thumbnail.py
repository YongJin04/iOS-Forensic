import os
import sqlite3
import io
from PIL import Image, ImageTk

import os
import sqlite3

def find_safari_thumbnails(backup_path):
    manifest_db_path = os.path.join(backup_path, "Manifest.db")
    if not os.path.exists(manifest_db_path):
        print("Manifest.db를 찾을 수 없습니다.")
        return None

    try:
        conn = sqlite3.connect(manifest_db_path)
        cursor = conn.cursor()

        query = """
            SELECT relativePath, fileID FROM Files 
            WHERE relativePath LIKE 'Library/Safari/Thumbnails/%'
        """
        cursor.execute(query)
        results = cursor.fetchall()

        if not results:
            print("Safari 썸네일 파일을 찾을 수 없습니다.")
            return None

        thumbnail_files = []
        for relative_path, file_id in results:
            resolved_path = os.path.normpath(os.path.join(backup_path, file_id[:2], file_id))


            if os.path.exists(resolved_path):
                thumbnail_files.append(resolved_path)
            else:
                print(f"존재하지 않는 파일: {resolved_path}")

        return thumbnail_files if thumbnail_files else None

    except sqlite3.Error as e:
        print(f"SQLite 오류: {e}")
    finally:
        conn.close()

    return None



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
        image_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

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
            except Exception as e:
                print(f"썸네일 처리 오류 ({img_path}): {str(e)}")
                continue

        if not thumbnails:
            return "Safari 썸네일 이미지가 없습니다."

        return thumbnails

    except Exception as e:
        return f"Safari 썸네일 로드 중 오류 발생: {str(e)}"


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
        print(f"이미지 변환 오류: {str(e)}")
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
