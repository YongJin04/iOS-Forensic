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

def render_preview(right: ttk.Frame, file_path: Path):
    for w in right.winfo_children():
        w.destroy()

    ext = file_path.suffix.lower()

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
                pdf_scrollbar.pack(side="right", fill="y", padx=(0,10), pady=10)

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

    elif ext == '.pptx':
        btn_external = ttk.Button(
            right,
            text="Open with External App",
            command=lambda p=file_path: _open_external(p)
        )
        btn_external.pack(side="bottom", pady=(5, 10))

        if not PptxPresentation:
            ttk.Label(right, text="⚠️ python-pptx not installed. Cannot preview PPTX.").pack(expand=True)
            return

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
            ttk.Label(right, text="⚠️ LibreOffice(soffice) not found. Cannot convert PPTX to image.").pack(expand=True)
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
            ], check=True)

            if not tmp_pdf.exists():
                ttk.Label(right, text="⚠️ PPTX → PDF 변환 실패.").pack(expand=True)
                return

            pdf_doc = fitz.open(str(tmp_pdf))
            total_slides = pdf_doc.page_count
            current_slide = 0

            container = ttk.Frame(right)
            container.pack(fill="both", expand=True)

            slide_canvas = tk.Canvas(container, width=500, highlightthickness=0)
            slide_scrollbar = ttk.Scrollbar(container, orient="vertical", command=slide_canvas.yview)
            slide_canvas.configure(yscrollcommand=slide_scrollbar.set)

            slide_canvas.pack(side="left", anchor="center", padx=10, pady=10, expand=True, fill="y")
            slide_scrollbar.pack(side="right", fill="y", padx=(0,10), pady=10)

            inner_frame = ttk.Frame(slide_canvas)
            slide_canvas.create_window((0, 0), window=inner_frame, anchor="nw")

            def render_slide(page_index):
                nonlocal current_slide
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
                    slide_canvas.configure(scrollregion=slide_canvas.bbox("all"))
                except Exception as e:
                    for widget in inner_frame.winfo_children():
                        widget.destroy()
                    ttk.Label(inner_frame, text=f"⚠️ Slide render error:\n{e}").pack()

            nav_frame = ttk.Frame(right)
            nav_frame.pack(fill="x", pady=(5, 0))
            prev_btn = ttk.Button(nav_frame, text="◀ Prev", command=lambda: show_slide(current_slide - 1))
            prev_btn.pack(side="left", padx=(5, 2))
            nav_lbl = ttk.Label(nav_frame, text=f"Slide 1 / {total_slides}")
            nav_lbl.pack(side="left", expand=True)
            next_btn = ttk.Button(nav_frame, text="Next ▶", command=lambda: show_slide(current_slide + 1))
            next_btn.pack(side="right", padx=(2, 5))

            def show_slide(new_index):
                nonlocal current_slide
                if new_index < 0:
                    new_index = 0
                if new_index >= total_slides:
                    new_index = total_slides - 1
                current_slide = new_index
                nav_lbl.config(text=f"Slide {current_slide + 1} / {total_slides}")
                render_slide(current_slide)

            show_slide(0)

            def _on_mousewheel(event):
                slide_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            slide_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        except subprocess.CalledProcessError as e:
            ttk.Label(right, text=f"⚠️ PPTX → PDF 변환 중 오류:\n{e}").pack(expand=True)
        except Exception as e:
            ttk.Label(right, text=f"⚠️ PPTX preview error: {e}").pack(expand=True)

    else:
        ttk.Label(right, text="⚠️ Unsupported file format.").pack(expand=True)
        ttk.Button(
            right,
            text="Open with External App",
            command=lambda p=file_path: _open_external(p)
        ).pack(pady=10)
