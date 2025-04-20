import tkinter as tk
from tkinter import ttk, messagebox, font
from PIL import Image, ImageTk
import io
import re
from artifact_analyzer.addressbook.addressbook_analyzer import AddressBookAnalyzer

class AddressBookApp:
    """
    iOS 백업 주소록 데이터를 분석하고, Tkinter UI로 표시하는 클래스.
    부모 위젯(Frame 또는 Tk)를 받아 그 안에 UI를 구성합니다.
    """
    def __init__(self, parent, backup_path: str):
        self.parent = parent
        self.backup_path = backup_path
        self.analyzer = AddressBookAnalyzer(backup_path)
        self.entries = []  # 로드된 연락처 리스트

        # 볼드체 폰트
        base_font = font.nametofont("TkDefaultFont")
        self.bold_font = base_font.copy()
        self.bold_font.configure(weight="bold")

        self._setup_styles()
        self._build_ui()
        self._load_entries_async()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Header.TLabel", font=("Helvetica", 16, "bold"))
        style.configure("Info.TLabel", font=("Helvetica", 12), foreground="#555")
        style.configure("Error.TLabel", font=("Helvetica", 12), foreground="#c33")
        style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"))

    def _build_ui(self):
        # 윈도우 환경일 경우 제목/크기 설정
        if isinstance(self.parent, tk.Tk):
            self.parent.title("주소록 분석기")
            self.parent.geometry("800x600")

        # 헤더
        header = ttk.Frame(self.parent, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="주소록 분석", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="검색:").pack(side="left", padx=(20,5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._populate_tree())
        ttk.Entry(header, textvariable=self.search_var, width=30).pack(side="left")

        # 로딩 메시지
        self.loading_label = ttk.Label(
            self.parent,
            text="연락처 로드 중...",
            style="Info.TLabel",
            padding=20
        )
        self.loading_label.pack()

        # 메인 분할
        self.content = ttk.Frame(self.parent)
        paned = ttk.PanedWindow(self.content, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=10, padx=10)
        self._build_list_view(paned)
        self._build_detail_view(paned)

    def _build_list_view(self, paned):
        frame = ttk.Frame(paned)
        paned.add(frame, weight=1)
        cols = ("name", "phone", "org", "rowid")
        self.tree = ttk.Treeview(
            frame,
            columns=cols,
            show="headings",
            selectmode="browse"
        )
        for col, text in zip(cols, ["이름", "전화번호", "소속", ""]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=150, anchor="w")
        self.tree["displaycolumns"] = ("name", "phone", "org")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection)

    def _build_detail_view(self, paned):
        frame = ttk.Frame(paned)
        paned.add(frame, weight=2)
        self.image_label = ttk.Label(frame)
        self.image_label.pack(pady=10)
        self.detail_text = tk.Text(frame, wrap="word", height=15)
        self.detail_text.tag_configure("bold", font=self.bold_font)
        self.detail_text.config(state="disabled")
        self.detail_text.pack(fill="both", expand=True)

    def _load_entries_async(self):
        self.parent.after(100, self._load_entries)

    def _load_entries(self):
        """
        AddressBookAnalyzer.load_entries()를 호출해 데이터를 로드하고,
        entries에 저장한 뒤 UI를 초기화합니다.
        """
        success, msg = self.analyzer.load_entries()
        self.loading_label.destroy()
        if not success:
            messagebox.showerror("오류", msg)
            ttk.Label(
                self.parent,
                text=f"연락처 로드 실패: {msg}",
                style="Error.TLabel",
                padding=20
            ).pack()
            return

        # 로드된 항목 저장 및 TreeView 초기화
        self.entries = self.analyzer.get_entries()
        self.content.pack(fill="both", expand=True)
        self._populate_tree()

    def _populate_tree(self):
        query = self.search_var.get().strip()
        filtered = self.analyzer.search_entries(query)

        # TreeView 갱신
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for entry in filtered:
            name = f"{entry.last_name} {entry.first_name}".strip()
            phone = entry.get_phone_number() or ""
            org = entry.organization or ""
            self.tree.insert(
                "",
                "end",
                values=(name, phone, org, entry.rowid)
            )

    def _on_selection(self, _):
        sel = self.tree.selection()
        if not sel:
            self._clear_details()
            return
        rowid = self.tree.item(sel[0], "values")[3]
        entry = next(
            (e for e in self.entries if str(e.rowid) == str(rowid)),
            None
        )
        if not entry:
            self._clear_details()
            return

        self._display_details(entry)

    def _clear_details(self):
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.config(state="disabled")
        self.image_label.config(image="")

    def _display_details(self, entry):
        # HTML-like 태그 파싱
        html = entry.get_formatted_details()
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", tk.END)
        parts = re.split(r'(<b>|</b>|<br>)', html)
        bold = False
        for p in parts:
            if p == "<b>": bold = True
            elif p == "</b>": bold = False
            elif p == "<br>": self.detail_text.insert(tk.END, "\n")
            else: self.detail_text.insert(
                tk.END,
                p,
                "bold" if bold else None
            )
        self.detail_text.config(state="disabled")

        # 이미지 표시
        if entry.image:
            try:
                img = Image.open(io.BytesIO(entry.image))
                img = img.resize((150, 150), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.image_label.config(image=photo)
                self.image_label.image = photo
            except:
                self.image_label.config(image="")
        else:
            self.image_label.config(image="")


def display_addressbook(parent_frame, backup_path: str) -> AddressBookApp:
    """
    부모 프레임에 주소록 UI를 삽입합니다.

    Args:
        parent_frame: Tk 또는 Frame 위젯
        backup_path: 주소록 백업 경로

    Returns:
        구성된 AddressBookApp 인스턴스
    """
    # 기존 위젯 제거
    for w in parent_frame.winfo_children():
        w.destroy()
    app = AddressBookApp(parent_frame, backup_path)
    return app