import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from PIL import Image, ImageTk, ImageEnhance  
from artifact_analyzer.browser.safari.thumbnail import *


def create_thumbnail_ui(parent):
    """
    브라우저 썸네일 UI 생성
    
    Args:
        parent: 상위 프레임
        
    Returns:
        scrollable_frame: 스크롤 가능한 썸네일 프레임
    """
    thumbnail_frame = ttk.Frame(parent, padding=15)
    thumbnail_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 스크롤바가 있는 캔버스 생성
    canvas_container = ttk.Frame(thumbnail_frame)
    canvas_container.pack(fill="both", expand=True)
    
    canvas = tk.Canvas(canvas_container)
    scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    return scrollable_frame





def clear_thumbnail_canvas(canvas):
    """
    썸네일 캔버스 초기화
    
    Args:
        canvas: 썸네일을 표시할 캔버스
    """
    for widget in canvas.winfo_children():
        widget.destroy()

def fetch_thumbnails(browser_name, thumbnail_canvas, backup_path):
    """
    선택한 브라우저의 썸네일 데이터 가져오기
    
    Args:
        browser_name: 브라우저 이름
        thumbnail_canvas: 썸네일 캔버스 위젯
        backup_path: 백업 파일 경로
    """
    # 캔버스 초기화
    clear_thumbnail_canvas(thumbnail_canvas)
    
    try:
        if browser_name == "Safari":
            thumbnails = get_safari_thumbnails(backup_path, max_thumbnails=50)
            display_thumbnails(thumbnail_canvas, thumbnails, browser_name)
        else:
            display_no_thumbnails_message(thumbnail_canvas, browser_name)
    
    except Exception as e:
        messagebox.showerror("오류", f"{browser_name} 썸네일 로드 중 오류 발생: {str(e)}")
        display_no_thumbnails_message(thumbnail_canvas, browser_name, error_msg=str(e))




def open_image_viewer(original_image, title="이미지 뷰어"):
    viewer = Toplevel()
    viewer.title(title)
    viewer.geometry("1000x800")
    viewer.state('zoomed')

    frame = ttk.Frame(viewer)
    frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(frame, highlightthickness=0, bd=0, background="black")
    h_scrollbar = ttk.Scrollbar(frame, orient="horizontal", command=canvas.xview)
    v_scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)

    canvas.grid(row=0, column=0, sticky="nsew")
    h_scrollbar.grid(row=1, column=0, sticky="ew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")

    canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
    
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    pil_image = None

    try:
        if isinstance(original_image, Image.Image):
            pil_image = original_image.copy()
        elif isinstance(original_image, ImageTk.PhotoImage):
            pil_image = ImageTk.getimage(original_image)
        else:
            pil_image = Image.new('RGB', (800, 600), color='white')
            print("기본 이미지 생성됨")
    except Exception as e:
        print(f"이미지 변환 오류: {e}")
        pil_image = Image.new('RGB', (800, 600), color='white')

    zoom_factor = 3.0

    def display_image(zoom=zoom_factor):
        try:
            if pil_image is not None:
                img_width, img_height = pil_image.size
                new_width = int(img_width * zoom)
                new_height = int(img_height * zoom)

                # 1. 슈퍼 샘플링: 더 크게 보간 후 축소하여 계단 현상 최소화
                super_sample_size = (new_width * 2, new_height * 2)
                super_sampled = pil_image.resize(super_sample_size, Image.Resampling.BICUBIC)

                # 2. 다시 원하는 크기로 다운샘플링하여 부드러운 효과 적용
                resized_img = super_sampled.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # 3. 선명도 보정
                enhancer = ImageEnhance.Sharpness(resized_img)
                enhanced_img = enhancer.enhance(1.5)  # 선명도를 높여 더 깨끗하게

                # 4. 대비 보정 (선택 사항, 필요 시 조정)
                contrast_enhancer = ImageEnhance.Contrast(enhanced_img)
                final_img = contrast_enhancer.enhance(1.2)  # 대비 증가

                photo = ImageTk.PhotoImage(final_img)
                canvas.delete("all")
                canvas.create_image(0, 0, anchor="nw", image=photo)
                canvas.image = photo
                
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.xview_moveto(0)
            canvas.yview_moveto(0)

        except Exception as e:
            print(f"이미지 확대 오류: {e}")
            canvas.delete("all")
            canvas.create_text(400, 300, text="이미지 표시 오류", fill="white")

    current_zoom = zoom_factor

    def zoom_in(event=None):
        nonlocal current_zoom
        current_zoom += 0.5
        display_image(current_zoom)

    def zoom_out(event=None):
        nonlocal current_zoom
        if current_zoom > 0.5:
            current_zoom -= 0.5
            display_image(current_zoom)

    viewer.bind("<plus>", zoom_in)
    viewer.bind("<minus>", zoom_out)
    viewer.bind("<equal>", zoom_in)
    canvas.bind("<MouseWheel>", lambda event: zoom_in() if event.delta > 0 else zoom_out())

    control_frame = ttk.Frame(viewer)
    control_frame.pack(fill="x", padx=10, pady=5)

    zoom_in_btn = ttk.Button(control_frame, text="확대 (+)", command=zoom_in)
    zoom_in_btn.pack(side="left", padx=5)

    zoom_out_btn = ttk.Button(control_frame, text="축소 (-)", command=zoom_out)
    zoom_out_btn.pack(side="left", padx=5)

    viewer.bind("<Escape>", lambda e: viewer.destroy())

    display_image()




def display_thumbnails(canvas, thumbnails, browser_name):
    """
    브라우저 썸네일을 화면에 표시
    
    Args:
        canvas: 썸네일을 표시할 캔버스
        thumbnails: 썸네일 데이터 목록 또는 오류 메시지
        browser_name: 브라우저 이름
    """

        # 썸네일 결과가 오류 메시지인 경우
    if isinstance(thumbnails, str):
        ttk.Label(canvas, text=thumbnails, font=("", 12)).pack(pady=50)
        return
    
    # 썸네일이 없는 경우
    if not thumbnails:
        ttk.Label(canvas, text=f"{browser_name} 브라우저의 썸네일을 찾을 수 없습니다.", font=("", 12)).pack(pady=50)
        return
    

    # 캔버스 크기 갱신 (초기 크기 가져오기)
    canvas.update_idletasks()  # 🔥 캔버스 크기 강제 업데이트
    parent_width = canvas.winfo_width()
    
    # 초기 실행 시 크기를 못 가져오는 경우 기본값 설정
    if parent_width < 400:
        parent_width = canvas.winfo_toplevel().winfo_width() or 800  # 창 크기 사용
    
    thumbnail_width = 180  # 썸네일 프레임 예상 너비
    column_count = max(3, parent_width // thumbnail_width)  # 최소 3열, 화면 크기에 따라 증가
    
    # 기존 내용 삭제
    for widget in canvas.winfo_children():
        widget.destroy()
    
    # 제목 추가
    title_label = ttk.Label(canvas, text=f"{browser_name} 브라우저 썸네일 ({len(thumbnails)}개)", font=("", 12, "bold"))
    title_label.grid(row=0, column=0, columnspan=column_count, pady=(0, 10), sticky="ew")

    row, col = 1, 0

    for thumb_data in thumbnails:
        try:
            # 브라우저에 따라 썸네일 처리 방식을 달리할 수 있음
            if browser_name == "Safari":
                thumbnail_result = get_thumbnail_image(thumb_data)
                if thumbnail_result is None:
                    continue
                    
                photo_image, file_name, original_size = thumbnail_result
                details = get_thumbnail_details(thumb_data)


                photo_image, file_name, original_size = thumbnail_result
                details = get_thumbnail_details(thumb_data)
                
                # 원본 이미지 객체 저장 (큰 이미지 뷰어용)
                # thumb_data는 튜플이므로 get() 메서드를 사용할 수 없음 - 수정 필요
                original_img = None
                try:
                    # 썸네일 이미지를 기반으로 원본 크기 이미지 생성 (확대본)
                    if isinstance(photo_image, ImageTk.PhotoImage):
                        # 썸네일 이미지를 원본 크기로 확대
                        scale_factor = 2
                        if isinstance(original_size, tuple) and len(original_size) == 2:
                            orig_width, orig_height = original_size
                            if orig_width > 0 and orig_height > 0:
                                # 원본 크기 비율 계산
                                scale_factor = max(orig_width / 150, orig_height / 100, 2)
                        # PIL 이미지로 변환하여 확대
                        original_img = photo_image
                except Exception as e:
                    print(f"원본 이미지 생성 오류: {e}")
                    original_img = photo_image
            else:
                # 다른 브라우저는 해당 브라우저에 맞는 처리 필요
                photo_image, file_name, details = process_thumbnail(browser_name, thumb_data)
                original_img = photo_image  # 임시로 썸네일 이미지 사용


            # 썸네일 프레임 생성
            thumb_frame = ttk.Frame(canvas, padding=5)
            thumb_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")  # 🔥 sticky="nsew" 추가
            
            # 이미지 표시
            img_label = ttk.Label(thumb_frame, image=photo_image, cursor="hand2")
            img_label.image = photo_image  # 참조 유지
            img_label.pack(pady=(0, 3), fill="both", expand=True)  # 🔥 확장

            # 파일명 표시 (짧게 표시)
            display_name = file_name
            if len(display_name) > 20:
                display_name = display_name[:17] + "..."
            ttk.Label(thumb_frame, text=display_name, wraplength=140).pack()
            
            # 썸네일 정보 표시
            if isinstance(details, dict) and 'original_width' in details:
                size_text = f"{details['original_width']}x{details['original_height']} ({details['file_size']}KB)"
                ttk.Label(thumb_frame, text=size_text, font=("", 8)).pack()

            # 썸네일 클릭 시 큰 이미지로 보기
            def show_large_image(img=original_img, name=file_name):
                open_image_viewer(img, f"이미지 뷰어 - {name}")
            
            img_label.bind("<Button-1>", lambda e, handler=show_large_image: handler())
             # 프레임 테두리에 호버 효과 추가
            def on_enter(e, frame=thumb_frame):
                frame.configure(style="Hover.TFrame")
            
            def on_leave(e, frame=thumb_frame):
                frame.configure(style="TFrame")
                
            thumb_frame.bind("<Enter>", on_enter)
            thumb_frame.bind("<Leave>", on_leave)

            # 다음 열로 이동
            col += 1
            if col >= column_count:
                col = 0
                row += 1
        
        except Exception as e:
            print(f"썸네일 표시 오류 ({browser_name}): {e}")

    for i in range(column_count):
        canvas.columnconfigure(i, weight=1)  # 가로 공간 균등 배분
    for i in range(row + 1):
        canvas.rowconfigure(i, weight=1)  # 세로 공간 균등 배분





def process_thumbnail(browser_name, thumb_data):
    """
    다른 브라우저의 썸네일 데이터를 처리하는 함수
    
    Args:
        browser_name: 브라우저 이름
        thumb_data: 썸네일 데이터
        
    Returns:
        (PhotoImage, 파일명, 상세 정보) 튜플
    """
    # 이 함수는 나중에 각 브라우저별로 구현해야 함
    # 현재는 더미 데이터 반환
    dummy_image = Image.new('RGB', (150, 100), color='gray')
    photo = ImageTk.PhotoImage(dummy_image)
    file_name = f"샘플_{browser_name}_썸네일.jpg"
    details = {
        'original_width': 1024,
        'original_height': 768,
        'file_size': 256
    }
    return (photo, file_name, details)




def display_no_thumbnails_message(canvas, browser_name, error_msg=None):
    """
    썸네일을 찾을 수 없을 때 메시지 표시
    
    Args:
        canvas: 메시지를 표시할 캔버스
        browser_name: |브라우저 이름
        error_msg: 선택적 오류 메시지
    """
    message_frame = ttk.Frame(canvas, padding=20)
    message_frame.pack(expand=True, fill="both")
    
    message = f"{browser_name} 브라우저의 썸네일을 찾을 수 없거나 아직 지원되지 않습니다."
    if error_msg:
        message += f"\n\n오류: {error_msg}"
        
    ttk.Label(
        message_frame, 
        text=message,
        font=("", 12),
        wraplength=400,
        justify="center"
    ).pack(pady=50)

# 앱 시작 시 스타일 설정을 추가
def setup_styles():
    """UI 스타일 설정"""
    style = ttk.Style()
    style.configure("Hover.TFrame", borderwidth=2, relief="raised")