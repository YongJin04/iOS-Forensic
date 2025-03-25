from tkinter import ttk, filedialog
import os
import sqlite3
import shutil
import threading
from PIL import Image, ImageTk
from datetime import datetime

def display_photos_media(content_frame, backup_path):
    """백업 데이터에서 사진 및 미디어 파일을 분석하고 표시합니다."""
    # 기존 위젯 삭제
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    # 헤더 추가
    header_frame = ttk.Frame(content_frame)
    header_frame.pack(fill="x", pady=(0, 10))
    
    ttk.Label(header_frame, text="🖼️ 사진 및 미디어", style="ContentHeader.TLabel").pack(side="left")
    ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=(0, 15))
    
    # 로딩 표시
    loading_frame = ttk.Frame(content_frame)
    loading_frame.pack(fill="both", expand=True)
    ttk.Label(loading_frame, text="미디어 파일을 분석 중입니다...", style="InfoValue.TLabel").pack(pady=20)
    progress = ttk.Progressbar(loading_frame, mode="indeterminate")
    progress.pack(fill="x", padx=50, pady=10)
    progress.start()
    
    # 백그라운드 스레드에서 미디어 분석 실행
    threading.Thread(target=lambda: analyze_media_files(content_frame, loading_frame, backup_path), daemon=True).start()

def analyze_media_files(content_frame, loading_frame, backup_path):
    """백업에서 미디어 파일을 분석하고 결과를 표시합니다."""
    try:
        # 미디어 정보 수집
        media_info = extract_media_info(backup_path)
        
        # UI 스레드에서 결과 표시
        content_frame.after(0, lambda: display_media_results(content_frame, loading_frame, media_info, backup_path))
    except Exception as e:
        # 오류 발생 시 오류 메시지 표시
        content_frame.after(0, lambda: display_error_message(content_frame, loading_frame, f"미디어 분석 중 오류가 발생했습니다: {str(e)}"))

def extract_media_info(backup_path):
    """백업 데이터에서 미디어 정보를 추출합니다."""
    # 예시 결과 데이터 (실제 구현에서는 백업 파일에서 데이터 추출)
    media_info = {
        "total_photos": 0,
        "total_videos": 0,
        "recent_media": [],
        "media_by_year": {},
        "media_by_month": {},
        "largest_files": []
    }
    
    # Photos.sqlite 또는 관련 데이터베이스 파일 찾기
    photos_db_path = find_database_file(backup_path, "Photos.sqlite")
    if photos_db_path:
        # 데이터베이스에서 미디어 정보 추출
        conn = sqlite3.connect(photos_db_path)
        cursor = conn.cursor()
        
        # 총 사진 수 (예시 쿼리, 실제 스키마에 맞게 수정 필요)
        try:
            cursor.execute("SELECT COUNT(*) FROM ZASSET WHERE ZKIND = 0")
            media_info["total_photos"] = cursor.fetchone()[0]
            
            # 총 비디오 수
            cursor.execute("SELECT COUNT(*) FROM ZASSET WHERE ZKIND = 1")
            media_info["total_videos"] = cursor.fetchone()[0]
            
            # 최근 미디어 (최대 10개)
            cursor.execute("""
                SELECT ZASSET.Z_PK, ZFILENAME, ZDATECREATED, ZKIND
                FROM ZASSET
                ORDER BY ZDATECREATED DESC
                LIMIT 10
            """)
            for row in cursor.fetchall():
                media_id, filename, created_date, kind = row
                media_type = "사진" if kind == 0 else "비디오"
                
                # Unix 타임스탬프를 datetime으로 변환 (iOS의 참조 날짜는 2001-01-01)
                if created_date:
                    ref_date = datetime(2001, 1, 1)
                    created_datetime = ref_date + datetime.timedelta(seconds=created_date)
                    date_str = created_datetime.strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = "알 수 없음"
                
                media_info["recent_media"].append({
                    "id": media_id,
                    "filename": filename,
                    "date": date_str,
                    "type": media_type
                })
        except Exception as e:
            print(f"미디어 데이터 추출 중 오류: {str(e)}")
        
        conn.close()
    
    # 일반 파일 시스템에서 미디어 파일 검색 (Media 폴더 등)
    media_folders = find_media_folders(backup_path)
    for folder in media_folders:
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
                    media_info["total_photos"] += 1
                elif file.lower().endswith(('.mp4', '.mov', '.m4v')):
                    media_info["total_videos"] += 1
    
    return media_info

def find_database_file(backup_path, db_name):
    """백업 폴더에서 지정된 데이터베이스 파일을 찾습니다."""
    for root, _, files in os.walk(backup_path):
        for file in files:
            if file == db_name:
                return os.path.join(root, file)
    return None

def find_media_folders(backup_path):
    """백업 폴더에서 미디어 관련 폴더를 찾습니다."""
    media_folders = []
    for root, dirs, _ in os.walk(backup_path):
        for dir_name in dirs:
            if "Media" in dir_name or "Photo" in dir_name or "Camera" in dir_name:
                media_folders.append(os.path.join(root, dir_name))
    return media_folders

def display_media_results(content_frame, loading_frame, media_info, backup_path):
    """미디어 분석 결과를 UI에 표시합니다."""
    # 로딩 프레임 제거
    loading_frame.destroy()
    
    # 미디어 통계 정보 카드
    stats_card = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
    stats_card.pack(fill="x", padx=5, pady=5)
    
    ttk.Label(stats_card, text="미디어 통계", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
    
    stats_grid = ttk.Frame(stats_card)
    stats_grid.pack(fill="x")
    
    # 통계 정보 표시
    stats_items = [
        {"label": "총 사진 수", "value": f"{media_info['total_photos']:,}개"},
        {"label": "총 비디오 수", "value": f"{media_info['total_videos']:,}개"},
        {"label": "총 미디어 파일", "value": f"{media_info['total_photos'] + media_info['total_videos']:,}개"},
    ]
    
    for i, item in enumerate(stats_items):
        col = i % 3
        
        # 레이블 + 값 프레임
        item_frame = ttk.Frame(stats_grid)
        item_frame.grid(row=0, column=col, sticky="w", padx=10, pady=5)
        
        ttk.Label(item_frame, text=item["label"] + ":", style="InfoLabel.TLabel").pack(anchor="w")
        ttk.Label(item_frame, text=item["value"], style="InfoValue.TLabel").pack(anchor="w")
    
    # 최근 미디어 파일 섹션
    if media_info["recent_media"]:
        recent_card = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
        recent_card.pack(fill="both", expand=True, padx=5, pady=5)
        
        ttk.Label(recent_card, text="최근 미디어 파일", style="CardSectionHeader.TLabel").pack(anchor="w", pady=(0, 10))
        
        # 섬네일과 정보를 표시할 그리드
        media_grid = ttk.Frame(recent_card)
        media_grid.pack(fill="both", expand=True)
        
        # 미디어 파일 별로 섬네일과 정보 표시 (최대 5개)
        for i, media in enumerate(media_info["recent_media"][:5]):
            # 미디어 항목 프레임
            media_frame = ttk.Frame(media_grid, style="MediaItem.TFrame", padding=10)
            media_frame.grid(row=i, column=0, sticky="ew", pady=5)
            
            # 썸네일 영역 (실제 구현에서는 이미지 로드)
            thumb_frame = ttk.Frame(media_frame, width=80, height=80, style="Thumbnail.TFrame")
            thumb_frame.pack(side="left", padx=(0, 10))
            thumb_frame.pack_propagate(False)
            
            # 썸네일 영역에 파일 타입 아이콘 표시
            icon_text = "🖼️" if media["type"] == "사진" else "🎬"
            ttk.Label(thumb_frame, text=icon_text, font=("Arial", 24)).pack(expand=True)
            
            # 미디어 정보
            info_frame = ttk.Frame(media_frame)
            info_frame.pack(side="left", fill="both", expand=True)
            
            ttk.Label(info_frame, text=media["filename"], style="MediaTitle.TLabel").pack(anchor="w")
            ttk.Label(info_frame, text=f"타입: {media['type']} | 날짜: {media['date']}", style="MediaInfo.TLabel").pack(anchor="w", pady=2)
            
            # 미디어 추출 버튼
            extract_btn = ttk.Button(media_frame, text="추출", 
                                     command=lambda m=media: extract_media_file(backup_path, m))
            extract_btn.pack(side="right")
    
    # 버튼 영역
    button_frame = ttk.Frame(content_frame)
    button_frame.pack(fill="x", pady=10)
    
    export_btn = ttk.Button(button_frame, text="모든 미디어 내보내기", 
                           command=lambda: export_all_media(backup_path))
    export_btn.pack(side="right", padx=5)

def extract_media_file(backup_path, media):
    """선택한 미디어 파일을 추출합니다."""
    # 파일 저장 대화상자
    save_path = filedialog.asksaveasfilename(
        title="미디어 파일 저장",
        initialfile=media["filename"],
        defaultextension=".*",
        filetypes=[("모든 파일", "*.*")]
    )
    
    if save_path:
        # 여기서 실제 파일 추출 로직 구현
        # 예: 백업에서 원본 파일 경로 찾아 복사
        pass

def export_all_media(backup_path):
    """모든 미디어 파일을 내보냅니다."""
    # 디렉토리 선택 대화상자
    export_dir = filedialog.askdirectory(title="미디어 내보내기 폴더 선택")
    
    if export_dir:
        # 여기서 실제 모든 파일 내보내기 구현
        # 진행 상황을 보여주는 대화상자를 표시할 수 있음
        pass

def display_error_message(content_frame, loading_frame, message):
    """오류 메시지를 표시합니다."""
    # 로딩 프레임 제거
    loading_frame.destroy()
    
    # 오류 메시지 프레임
    error_frame = ttk.Frame(content_frame, style="ErrorCard.TFrame", padding=15)
    error_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 오류 아이콘과 메시지
    ttk.Label(error_frame, text="⚠️", font=("Arial", 24)).pack(pady=(0, 10))
    ttk.Label(error_frame, text=message, style="ErrorText.TLabel", wraplength=400).pack()