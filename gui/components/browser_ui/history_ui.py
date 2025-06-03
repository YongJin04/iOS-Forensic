import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime

# Safari 기존 함수
from artifact_analyzer.browser.safari.history import get_safari_history as get_history
from artifact_analyzer.browser.chrome.snss_parser import parse_snss_session

# ────────────────────────────────────────────────
# 공통: 타임스탬프 문자열 포매팅
# ────────────────────────────────────────────────

def _format_timestamp(ts):
    """정수를 epoch 로, 문자열·datetime 은 그대로 파싱해
    "2025-05-31 AM 2:24:31" 형태로 반환."""
    if ts is None:
        return ""

    if isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts)
    elif isinstance(ts, datetime):
        dt = ts
    else:  # 문자열 등은 ISO-format 추정
        try:
            dt = datetime.fromisoformat(str(ts))
        except Exception:
            return str(ts)

    ampm = dt.strftime("%p")
    hour = dt.strftime("%I").lstrip("0") or "0"
    return f"{dt.strftime('%Y-%m-%d')} {ampm} {hour}:{dt.strftime('%M:%S')}"


# ────────────────────────────────────────────────
# Chrome SNSS-탭 → (title, url, timestamp) 리스트
# ────────────────────────────────────────────────

def _is_valid_web_url(url: str) -> bool:
    """http/https 로 시작하고 chrome:// 등 내부 페이지·북마크·썸네일 제외"""
    if not url:
        return False
    lowered = url.lower()
    if not lowered.startswith(("http://", "https://")):
        return False
    if lowered.startswith((
        "http://chrome://",
        "https://chrome://",
        "http://chrome-native://",
        "https://chrome-native://",
        "http://edge://",
        "https://edge://",
    )):
        return False
    if any(keyword in lowered for keyword in ("thumbnail", "썸네일", "bookmarks", "북마크")):
        return False
    return True


def get_chrome_history(backup_path: str | Path):
    """Chrome ‘현재 탭’·‘최종 탭’ 기록을 파싱해 (title, url, timestamp) 반환."""
    backup_path = Path(backup_path)

    now_file = backup_path / "fe" / "fe90cf53890f383fb2b28ec36ac2b5d8a678eaec"
    last_file = backup_path / "27" / "27598ef0cedfcb929996cc6f9112a95ad1cd0fd7"

    records: list[tuple[str, str, int | float | str | datetime]] = []

    def _append_records(snss_file: Path):
        if not snss_file.exists():
            return
        for rec in parse_snss_session(snss_file):
            url = rec.get("url", "")
            if not _is_valid_web_url(url):
                continue
            title = rec.get("title") or ""
            records.append((title, url, rec.get("timestamp")))

    _append_records(now_file)
    _append_records(last_file)
    return records


# (선택) 다른 브라우저용 더미 함수 – 오류 방지용

def get_firefox_history(_):
    return []

def get_edge_history(_):
    return []


# UI: Treeview 생성 – 검색 기록

def create_history_ui(parent):
    """검색 기록 탭(Treeview) 생성 – 열 순서: URL, Title, VisitTime"""
    browser_card = ttk.Frame(parent, padding=15)
    browser_card.pack(fill="both", expand=True, padx=5, pady=5)

    columns = ("url", "title", "visit_time")
    history_tree = ttk.Treeview(browser_card, columns=columns, show="headings")

    history_tree.heading("url", text="URL", anchor="w")
    history_tree.heading("title", text="Title", anchor="w")
    history_tree.heading("visit_time", text="Visit Time", anchor="w")

    history_tree.column("url", width=380, anchor="w")
    history_tree.column("title", width=240, anchor="w")
    history_tree.column("visit_time", width=170, anchor="w")

    history_tree.tag_configure("even", background="#FFFFFF")
    history_tree.tag_configure("odd", background="#f5f5f5")

    vsb = ttk.Scrollbar(browser_card, orient="vertical", command=history_tree.yview)
    history_tree.configure(yscrollcommand=vsb.set)

    history_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    vsb.pack(side="right", fill="y", pady=5)

    return history_tree


def fetch_history(browser_name: str, history_tree: ttk.Treeview, backup_path: str | Path):
    """선택 브라우저 기록 로드 후 Treeview 에 표시"""
    history_tree.delete(*history_tree.get_children())

    try:
        if browser_name == "Safari":
            history = get_history(backup_path)
        elif browser_name == "Chrome":
            history = get_chrome_history(backup_path)
        else:
            history = f"{browser_name} 브라우저 기록 로드 기능이 아직 구현되지 않았습니다."

        if isinstance(history, str):
            history_tree.insert("", "end", values=("", history, ""), tags=("even",))
            return

        if not history:
            history_tree.insert("", "end", values=("", "검색 기록이 없습니다.", ""), tags=("even",))
            return

        for idx, (title, url, ts) in enumerate(history):
            title = "" if (title or "").strip() in {"(제목 없음)", ""} else title
            visit_time = _format_timestamp(ts)
            tag = "even" if idx % 2 == 0 else "odd"
            history_tree.insert("", "end", values=(url, title, visit_time), tags=(tag,))

    except Exception as e:
        if browser_name != "Chrome":  # Chrome 은 팝업 생략
            messagebox.showerror("오류", f"{browser_name} 검색 기록 로드 중 오류 발생: {e}")
        history_tree.insert("", "end", values=("", f"오류: {e}", ""), tags=("even",))
