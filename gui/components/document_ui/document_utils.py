from tkinter import ttk, messagebox
import tkinter as tk
from pathlib import Path
import os
import platform
import subprocess
import tempfile
import shutil

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

try:
    import fitz
except ImportError:
    fitz = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    from pptx import Presentation as PptxPresentation
except ImportError:
    PptxPresentation = None

# 신규 import: pandas를 써서 .xlsx/.csv 읽기
try:
    import pandas as pd
except ImportError:
    pd = None

from tkinter.scrolledtext import ScrolledText


def _open_external(filepath: Path):
    try:
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":
            subprocess.call(["open", str(filepath)])
        else:
            subprocess.call(["xdg-open", str(filepath)])
    except Exception as e:
        messagebox.showerror("Open Error", str(e))


def render_preview(right: ttk.Frame, file_path: Path, ext):
    # 기존 위젯 제거
    for w in right.winfo_children():
        w.destroy()

    # ─────────────────────────────────────────────────────────────
    # 1) 이미지 파일
    # ─────────────────────────────────────────────────────────────
    if ext in {'.png', '.jpg', '.jpeg', '.gif'} and Image and ImageTk:
        try:
            img = Image.open(file_path)
            img.thumbnail((340, 340))
            photo = ImageTk.PhotoImage(img)
            lbl = ttk.Label(right, image=photo)
            lbl.image = photo
            lbl.pack(expand=True)
        except Exception as e:
            ttk.Label(right, text=f"⚠️ Image load error: {e}").pack(expand=True)

        ttk.Button(
            right,
            text="Open with External App",
            command=lambda p=file_path: _open_external(p)
        ).pack(pady=10)

    # ─────────────────────────────────────────────────────────────
    # 2) PDF 파일
    # ─────────────────────────────────────────────────────────────
    elif ext == '.pdf':
        btn_external = ttk.Button(
            right,
            text="Open with External App",
            command=lambda p=file_path: _open_external(p)
        )
        btn_external.pack(side="bottom", pady=(5, 10))

        if not fitz:
            ttk.Label(right, text="⚠️ PyMuPDF not installed. Cannot preview PDF.").pack(expand=True)
            return

        try:
            pdf_doc = fitz.open(str(file_path))
            total_pages = pdf_doc.page_count

            if total_pages == 1:
                page = pdf_doc.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.thumbnail((500, 700))
                photo = ImageTk.PhotoImage(img)

                lbl_img = ttk.Label(right, image=photo)
                lbl_img.image = photo
                lbl_img.pack(expand=True)

            else:
                current_page = 0
                container = ttk.Frame(right)
                container.pack(fill="both", expand=True)

                pdf_canvas = tk.Canvas(container, width=500, highlightthickness=0)
                pdf_scrollbar = ttk.Scrollbar(container, orient="vertical", command=pdf_canvas.yview)
                pdf_canvas.configure(yscrollcommand=pdf_scrollbar.set)

                pdf_canvas.pack(side="left", anchor="center", padx=10, pady=10, expand=True, fill="y")
                pdf_scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

                inner_frame = ttk.Frame(pdf_canvas)
                pdf_canvas.create_window((0, 0), window=inner_frame, anchor="nw")

                def render_pdf_page(page_index):
                    nonlocal current_page
                    try:
                        page = pdf_doc.load_page(page_index)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        img.thumbnail((500, 9999))
                        photo = ImageTk.PhotoImage(img)

                        for widget in inner_frame.winfo_children():
                            widget.destroy()

                        lbl_img = ttk.Label(inner_frame, image=photo)
                        lbl_img.image = photo
                        lbl_img.pack(pady=10)

                        inner_frame.update_idletasks()
                        pdf_canvas.configure(scrollregion=pdf_canvas.bbox("all"))
                    except Exception as e:
                        for widget in inner_frame.winfo_children():
                            widget.destroy()
                        ttk.Label(inner_frame, text=f"⚠️ PDF page render error:\n{e}").pack()

                nav_frame = ttk.Frame(right)
                nav_frame.pack(fill="x", pady=(5, 0))
                prev_btn = ttk.Button(nav_frame, text="◀ Prev", command=lambda: show_pdf_page(current_page - 1))
                prev_btn.pack(side="left", padx=(5, 2))
                page_label = ttk.Label(nav_frame, text=f"Page 1 / {total_pages}")
                page_label.pack(side="left", expand=True)
                next_btn = ttk.Button(nav_frame, text="Next ▶", command=lambda: show_pdf_page(current_page + 1))
                next_btn.pack(side="right", padx=(2, 5))

                def show_pdf_page(new_index):
                    nonlocal current_page
                    if new_index < 0:
                        new_index = 0
                    if new_index >= total_pages:
                        new_index = total_pages - 1
                    current_page = new_index
                    page_label.config(text=f"Page {current_page + 1} / {total_pages}")
                    render_pdf_page(current_page)

                show_pdf_page(0)

                def _on_mousewheel(event):
                    pdf_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                pdf_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        except Exception as e:
            ttk.Label(right, text=f"⚠️ PDF load error: {e}").pack(expand=True)

    # ─────────────────────────────────────────────────────────────
    # 3) DOCX 파일
    # ─────────────────────────────────────────────────────────────
    elif ext == '.docx':
        btn_external = ttk.Button(
            right,
            text="Open with External App",
            command=lambda p=file_path: _open_external(p)
        )
        btn_external.pack(side="bottom", pady=(5, 10))

        if not Document:
            ttk.Label(right, text="⚠️ python-docx not installed. Cannot preview DOCX.").pack(expand=True)
            return
        try:
            doc = Document(str(file_path))
            text_widget = ScrolledText(right, wrap="word")
            text_widget.pack(fill="both", expand=True, padx=5, pady=5)
            for para in doc.paragraphs:
                text_widget.insert("end", para.text + "\n")
            text_widget.configure(state="disabled")
        except Exception as e:
            ttk.Label(right, text=f"⚠️ DOCX read error: {e}").pack(expand=True)

    # ─────────────────────────────────────────────────────────────
    # 4) PPTX 파일 (기존 로직 유지)
    # ─────────────────────────────────────────────────────────────
    elif ext == '.pptx':
        # “외부 앱으로 열기” 버튼
        btn_external = ttk.Button(
            right,
            text="Open with External App",
            command=lambda p=file_path: _open_external(p)
        )
        btn_external.pack(side="bottom", pady=(5, 10))

        pdf_path = None
        temp_pdf_created = False

        # 1) Windows + PowerPoint COM 자동화 시도
        if platform.system() == "Windows":
            try:
                import pythoncom
                from win32com import client

                abs_pptx = os.path.abspath(str(file_path))
                if not os.path.exists(abs_pptx):
                    raise FileNotFoundError(f"PPTX 파일을 찾을 수 없습니다: {abs_pptx}")

                pythoncom.CoInitialize()
                ppt_app = client.Dispatch("PowerPoint.Application")

                # ------------------------------
                # [변경] PowerPoint 창을 완전히 숨기면 일부 버전에서 오류가 나므로,
                # Visible=1 로 실행한 뒤 곧바로 최소화(minimize) 처리
                ppt_app.Visible = 1
                ppt_app.DisplayAlerts = False                      # 알림창 꺼 두기
                ppt_app.WindowState = 2  # ppWindowMinimized → 최소화
                # ------------------------------

                # WithWindow=False → 창을 띄우지 않고 백그라운드 모드,
                # ReadOnly=True → 읽기 전용
                pres = ppt_app.Presentations.Open(abs_pptx, WithWindow=False, ReadOnly=True)

                # 임시 PDF 생성
                fd, temp_pdf = tempfile.mkstemp(suffix=".pdf")
                os.close(fd)

                # FileFormat=32 → PDF
                pres.SaveAs(temp_pdf, FileFormat=32)

                pres.Close()
                ppt_app.Quit()

                pdf_path = temp_pdf
                temp_pdf_created = True
            except Exception as e:
                # COM 변환 실패 시, 아래 LibreOffice로 넘김
                pdf_path = None
                try:
                    ppt_app.Quit()
                except:
                    pass

        # 2) LibreOffice(soffice) 방식으로 PPTX → PDF 변환 (COM 실패 또는 Windows가 아닐 때)
        if not pdf_path:
            # soffice(또는 libreoffice) 경로 찾기
            soffice_path = shutil.which("soffice") or shutil.which("libreoffice")
            if platform.system() == "Windows" and not soffice_path:
                win_paths = [
                    r"C:\Program Files\LibreOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
                ]
                for p in win_paths:
                    if Path(p).exists():
                        soffice_path = p
                        break

            if not soffice_path:
                ttk.Label(right, text="⚠️ LibreOffice(soffice)를 찾을 수 없습니다. PPTX → PDF 변환이 불가합니다.").pack(expand=True)
                return

            try:
                temp_dir = Path(tempfile.gettempdir())
                tmp_pdf = temp_dir / f"{file_path.stem}.pdf"
                if tmp_pdf.exists():
                    try:
                        tmp_pdf.unlink()
                    except:
                        pass

                subprocess.run([
                    soffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(temp_dir),
                    str(file_path)
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                if not tmp_pdf.exists():
                    raise RuntimeError("LibreOffice 변환 후에도 PDF가 생성되지 않았습니다.")

                pdf_path = str(tmp_pdf)
                temp_pdf_created = True
            except subprocess.CalledProcessError as e:
                ttk.Label(right, text=f"⚠️ PPTX → PDF 변환 중 오류 발생:\n{e}").pack(expand=True)
                return
            except Exception as e:
                ttk.Label(right, text=f"⚠️ PPTX → PDF 처리 오류:\n{e}").pack(expand=True)
                return

        # 3) PyMuPDF(fitz)가 설치되어 있어야 PDF 렌더링 가능
        if not fitz:
            ttk.Label(right, text="⚠️ PyMuPDF가 설치되어 있지 않습니다. PDF 미리보기를 할 수 없습니다.").pack(expand=True)
            return

        # 4) pdf_path 를 열어서, 기존 PDF 미리보기 코드와 동일하게 렌더링
        try:
            pdf_doc = fitz.open(str(pdf_path))
            total_pages = pdf_doc.page_count
            current_page = 0

            container = ttk.Frame(right)
            container.pack(fill="both", expand=True)

            slide_canvas = tk.Canvas(container, width=500, highlightthickness=0)
            slide_scrollbar = ttk.Scrollbar(container, orient="vertical", command=slide_canvas.yview)
            slide_canvas.configure(yscrollcommand=slide_scrollbar.set)

            slide_canvas.pack(side="left", anchor="center", padx=10, pady=10, expand=True, fill="y")
            slide_scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

            inner_frame = ttk.Frame(slide_canvas)
            slide_canvas.create_window((0, 0), window=inner_frame, anchor="nw")

            def render_slide(index):
                nonlocal current_page
                try:
                    page = pdf_doc.load_page(index)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img.thumbnail((500, 9999))
                    photo = ImageTk.PhotoImage(img)

                    # 이전 렌더된 위젯 모두 삭제
                    for widget in inner_frame.winfo_children():
                        widget.destroy()

                    lbl_img = ttk.Label(inner_frame, image=photo)
                    lbl_img.image = photo
                    lbl_img.pack(pady=10)

                    inner_frame.update_idletasks()
                    slide_canvas.configure(scrollregion=slide_canvas.bbox("all"))
                except Exception as e:
                    for widget in inner_frame.winfo_children():
                        widget.destroy()
                    ttk.Label(inner_frame, text=f"⚠️ Slide render error:\n{e}").pack()

            nav_frame = ttk.Frame(right)
            nav_frame.pack(fill="x", pady=(5, 0))
            prev_btn = ttk.Button(nav_frame, text="◀ Prev", command=lambda: show_slide(current_page - 1))
            prev_btn.pack(side="left", padx=(5, 2))
            nav_lbl = ttk.Label(nav_frame, text=f"Slide 1 / {total_pages}")
            nav_lbl.pack(side="left", expand=True)
            next_btn = ttk.Button(nav_frame, text="Next ▶", command=lambda: show_slide(current_page + 1))
            next_btn.pack(side="right", padx=(2, 5))

            def show_slide(new_index):
                nonlocal current_page
                if new_index < 0:
                    new_index = 0
                elif new_index >= total_pages:
                    new_index = total_pages - 1
                current_page = new_index
                nav_lbl.config(text=f"Slide {current_page + 1} / {total_pages}")
                render_slide(current_page)

            # 첫 슬라이드 렌더링
            show_slide(0)

            def _on_mousewheel(event):
                slide_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            slide_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        except Exception as e:
            ttk.Label(right, text=f"⚠️ PPTX preview error: {e}").pack(expand=True)

        finally:
            # 임시 PDF 파일(cleanup) : COM 또는 LibreOffice로 생성된 PDF 삭제
            if temp_pdf_created and pdf_path:
                try:
                    os.remove(pdf_path)
                except:
                    pass

    # ─────────────────────────────────────────────────────────────
    # 5) TXT 파일
    # ─────────────────────────────────────────────────────────────
    elif ext == '.txt':
        btn_external = ttk.Button(
            right,
            text="Open with External App",
            command=lambda p=file_path: _open_external(p)
        )
        btn_external.pack(side="bottom", pady=(5, 10))

        try:
            text_widget = ScrolledText(right, wrap="word")
            text_widget.pack(fill="both", expand=True, padx=5, pady=5)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    text_widget.insert("end", line)
            text_widget.configure(state="disabled")
        except Exception as e:
            ttk.Label(right, text=f"⚠️ TXT read error: {e}").pack(expand=True)

    # ─────────────────────────────────────────────────────────────
    # 6) CSV 파일
    # ─────────────────────────────────────────────────────────────
    elif ext == '.csv':
        btn_external = ttk.Button(
            right,
            text="Open with External App",
            command=lambda p=file_path: _open_external(p)
        )
        btn_external.pack(side="bottom", pady=(5, 10))

        if not pd:
            ttk.Label(right, text="⚠️ pandas not installed. Cannot preview CSV.").pack(expand=True)
            return

        try:
            # 먼저 UTF-8로 시도하고, 실패하면 CP949(또는 euc-kr)로 재시도
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='cp949')

            # DataFrame을 문자열로 변환하여 ScrolledText에 출력
            text_widget = ScrolledText(right, wrap="none")
            text_widget.pack(fill="both", expand=True, padx=5, pady=5)
            text_widget.insert("end", df.to_string(index=False))
            text_widget.configure(state="disabled")
        except Exception as e:
            ttk.Label(right, text=f"⚠️ CSV read error: {e}").pack(expand=True)

    # ─────────────────────────────────────────────────────────────
    # 7) XLSX 파일
    # ─────────────────────────────────────────────────────────────
    elif ext == '.xlsx':
        btn_external = ttk.Button(
            right,
            text="Open with External App",
            command=lambda p=file_path: _open_external(p)
        )
        btn_external.pack(side="bottom", pady=(5, 10))

        if not pd:
            ttk.Label(right, text="⚠️ pandas not installed. Cannot preview XLSX.").pack(expand=True)
            return

        try:
            # pandas로 첫 번째 시트 읽기 (openpyxl 엔진 사용)
            df = pd.read_excel(file_path, engine='openpyxl')
            # ScrolledText에 DataFrame을 문자열로 출력
            text_widget = ScrolledText(right, wrap="none")
            text_widget.pack(fill="both", expand=True, padx=5, pady=5)
            text_widget.insert("end", df.to_string(index=False))
            text_widget.configure(state="disabled")
        except Exception as e:
            ttk.Label(right, text=f"⚠️ XLSX read error: {e}").pack(expand=True)

    else:
        ttk.Label(right, text="⚠️ Unsupported file format.").pack(expand=True)
        ttk.Button(
            right,
            text="Open with External App",
            command=lambda p=file_path: _open_external(p)
        ).pack(pady=10)
