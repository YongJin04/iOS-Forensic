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

        # 한글 초성 매핑
        self.korean_consonants = {
            'ㄱ': ['가', '까', '깨', '고', '교', '구', '규', '그', '기', '까'],
            'ㄴ': ['나', '너', '노', '뇨', '누', '느', '니'],
            'ㄷ': ['다', '따', '더', '떠', '도', '두', '드', '디'],
            'ㄹ': ['라', '래', '러', '레', '로', '루', '르', '리'],
            'ㅁ': ['마', '매', '머', '메', '모', '무', '므', '미'],
            'ㅂ': ['바', '빠', '배', '뻬', '보', '뽀', '부', '뿌', '브', '비'],
            'ㅅ': ['사', '싸', '새', '쌔', '서', '써', '소', '쏘', '수', '쑤', '스', '시', '씨'],
            'ㅇ': ['아', '애', '어', '에', '오', '우', '으', '이'],
            'ㅈ': ['자', '짜', '재', '째', '저', '져', '조', '좌', '주', '쥬', '즈', '지', '찌'],
            'ㅊ': ['차', '채', '처', '체', '초', '추', '츄', '츠', '치'],
            'ㅋ': ['카', '캐', '커', '케', '코', '쿠', '크', '키'],
            'ㅌ': ['타', '태', '터', '테', '토', '투', '트', '티'],
            'ㅍ': ['파', '패', '퍼', '페', '포', '푸', '프', '피'],
            'ㅎ': ['하', '해', '허', '헤', '호', '후', '흐', '히']
        }

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
        
        # 검색 프레임
        search_frame = ttk.Frame(header)
        search_frame.pack(side="left", padx=(20, 0))
        
        # 검색 타입 선택
        ttk.Label(search_frame, text="검색 유형:").pack(side="left", padx=(0, 5))
        self.search_type = tk.StringVar(value="전체")
        search_combo = ttk.Combobox(search_frame, textvariable=self.search_type, width=10, state="readonly")
        search_combo['values'] = ('전체', '이름', '전화번호')
        search_combo.current(0)
        search_combo.pack(side="left", padx=(0, 10))
        search_combo.bind("<<ComboboxSelected>>", lambda *_: self._populate_tree())
        
        # 검색어 입력
        ttk.Label(search_frame, text="검색어:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._populate_tree())
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side="left")

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

    def _get_display_name(self, entry):
        """
        None 값이 아닌 이름 구성 요소만 사용하여 표시 이름을 반환합니다.
        """
        last_name = entry.last_name if entry.last_name and entry.last_name != "None" else ""
        first_name = entry.first_name if entry.first_name and entry.first_name != "None" else ""
        # 둘 다 없는 경우 '이름 없음' 반환
        if not last_name and not first_name:
            return "이름 없음"
        return f"{last_name} {first_name}".strip()

    def _populate_tree(self):
        query = self.search_var.get().strip()
        search_type = self.search_type.get()
        
        # 검색 유형에 따라 필터링
        if not query:
            filtered = self.entries  # 검색어가 없으면 모든 항목 표시
        else:
            if search_type == '이름':
                filtered = self._search_by_name(query)
            elif search_type == '전화번호':
                filtered = self._search_by_phone(query)
            else:  # '전체'
                filtered = self._search_all(query)

        # TreeView 갱신
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for entry in filtered:
            name = self._get_display_name(entry)
            phone = entry.get_phone_number() or ""
            org = entry.organization or ""
            # "None" 문자열이 표시되지 않도록 처리
            if org == "None":
                org = ""
            self.tree.insert(
                "",
                "end",
                values=(name, phone, org, entry.rowid)
            )

    def _is_consonant_search(self, query):
        """쿼리가 한글 자음을 포함하는지 확인"""
        return any(c in self.korean_consonants for c in query)

    def _search_by_name(self, query):
        """이름으로 검색 (한글 자음 검색 및 부분 문자열 검색 통합)"""
        result = []
        query = query.lower()
        
        # 자음을 포함한 검색인지 확인
        has_consonant = self._is_consonant_search(query)
        
        for entry in self.entries:
            full_name = self._get_display_name(entry)
            full_name_lower = full_name.lower()
            
            # 일반 문자열 부분 검색 - 자음이 없는 경우 항상 수행
            if not has_consonant:
                if query in full_name_lower:
                    result.append(entry)
                    continue
            else:
                # 자음이 포함된 경우 - 연속된 초성 검색 로직
                current_pos = 0
                query_pos = 0
                match_started = False
                match_length = 0
                
                while query_pos < len(query) and current_pos < len(full_name):
                    current_char = query[query_pos]
                    
                    # 현재 글자가 자음인 경우
                    if current_char in self.korean_consonants:
                        found = False
                        # 현재 위치부터 이름의 나머지 부분을 검사
                        for check_pos in range(current_pos, len(full_name)):
                            name_char = full_name[check_pos]
                            # 해당 자음으로 시작하는 글자인지 확인
                            for start_char in self.korean_consonants[current_char]:
                                if name_char.startswith(start_char[0]):
                                    if not match_started:
                                        match_started = True
                                        current_pos = check_pos
                                    current_pos = check_pos + 1
                                    match_length += 1
                                    found = True
                                    break
                            if found:
                                break
                    else:
                        # 일반 글자인 경우 정확히 일치하는지 확인
                        found = False
                        for check_pos in range(current_pos, len(full_name)):
                            if query[query_pos].lower() == full_name[check_pos].lower():
                                if not match_started:
                                    match_started = True
                                    current_pos = check_pos
                                current_pos = check_pos + 1
                                match_length += 1
                                found = True
                                break
                    
                    if not found:
                        break
                    
                    query_pos += 1
                
                # 모든 쿼리 글자가 매칭되었으면 결과에 추가
                if query_pos == len(query):
                    result.append(entry)
                    continue
                
                # 자음이 포함된 경우에도 일반 문자열 부분 검색 시도
                # 이것은 '이승'과 같은 연속된 글자 검색을 위함
                if query in full_name_lower:
                    result.append(entry)
        
        return result
    
    def _search_by_phone(self, query):
        """전화번호로 검색"""
        result = []
        # 숫자만 추출해서 비교
        query = ''.join(c for c in query if c.isdigit())
        for entry in self.entries:
            phone = entry.get_phone_number() or ""
            phone_digits = ''.join(c for c in phone if c.isdigit())
            if query in phone_digits:
                result.append(entry)
        return result
    
    def _search_all(self, query):
        """이름과 전화번호 모두 검색 (중복 제거)"""
        # 이름 검색 결과
        name_results = self._search_by_name(query)
        
        # 전화번호 검색 결과 (숫자가 있는 경우만)
        phone_results = []
        if any(c.isdigit() for c in query):
            phone_results = self._search_by_phone(query)
        
        # 중복 제거를 위해 dictionary로 변환 후 다시 리스트로
        result_dict = {entry.rowid: entry for entry in name_results + phone_results}
        return list(result_dict.values())

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
        
        # "None" 문자열 제거 처리
        html = html.replace(">None<", "><")
        html = re.sub(r'<b>None</b>', '', html)
        
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