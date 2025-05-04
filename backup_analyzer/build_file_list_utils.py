"""
파일‑리스트(TreeView) 구축 + Manifest.db / bplist 메타데이터 처리
아이콘은 Tk 루트가 준비된 뒤 첫 호출 시 Lazy‑Load 된다.
"""

from __future__ import annotations

import os
import sqlite3
import plistlib
from datetime import datetime
from typing import Dict, Any, Tuple
from tkinter import ttk, PhotoImage, Widget

# ────────────────────────────────────────────────────────────────
# 1) 아이콘 (lazy‑load)
# ────────────────────────────────────────────────────────────────
_ICON_DICT: dict[str, PhotoImage] = {}  # 첫 호출 때 채워짐


def _ensure_icons(master_widget: Widget) -> None:
    """Tk 루트가 준비된 뒤 한 번만 PhotoImage 객체를 생성한다."""
    if _ICON_DICT:  # 이미 로드됨
        return

    base = os.path.join(os.path.dirname(__file__), "..", "gui", "icon")

    def _icon(fname: str) -> PhotoImage:
        return PhotoImage(master=master_widget, file=os.path.join(base, fname)).subsample(
            30, 30
        )

    _ICON_DICT.update({
        "folder": _icon("folder.png"),
        "file": _icon("file.png"),
        "image": _icon("file.png"),
    })


def get_file_icon(filename: str) -> str:
    """확장자에 따라 'image' / 'file' 키 반환"""
    if filename.lower().endswith(
        (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic", ".dng", ".aae")
    ):
        return "image"
    return "file"


# ────────────────────────────────────────────────────────────────
# 2) bplist 메타데이터 유틸
# ────────────────────────────────────────────────────────────────

def mode_to_rwx(mode: int) -> str:
    perms = ["r", "w", "x"]
    out = ""
    for shift in (6, 3, 0):
        bits = (mode >> shift) & 0b111
        out += "".join(perms[i] if (bits & (1 << (2 - i))) else "-" for i in range(3))
    return out


def fmt_ts(ts: int | None) -> str:
    if ts is None:
        return ""
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def parse_bplist_metadata(blob: bytes | None) -> Tuple[int | None, str, str, str]:
    """bplist00 → (size, mdate, cdate, perm)"""
    if not blob:
        return None, "", "", ""
    try:
        plist = plistlib.loads(blob)
        root = plist["$objects"][plist["$top"]["root"].data]
        size = root.get("Size")
        mdate = fmt_ts(root.get("LastModified"))
        cdate = fmt_ts(root.get("Birth"))
        perm = mode_to_rwx(root.get("Mode")) if root.get("Mode") else ""
        return f"{size:,}" if size is not None else None, mdate, cdate, perm
    except Exception as e:
        print(f"[bplist parse error] {e}")
        return None, "", "", ""


# ────────────────────────────────────────────────────────────────
# 3) Manifest.db 조회
# ────────────────────────────────────────────────────────────────

def get_flags_and_file(backup_path: str, domain: str, rel_path: str):
    db_path = os.path.join(backup_path, "Manifest.db")
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT flags, file FROM Files WHERE domain=? AND relativePath=?",
                (domain, rel_path),
            )
            return cur.fetchone() or (None, None)
    except Exception as e:
        print(f"[DB Error] {e}")
        return None, None


# ────────────────────────────────────────────────────────────────
# 4) Directory Size 계산 (1‑계층)
# ────────────────────────────────────────────────────────────────

def _sum_first_level_file_sizes(child_dict: Dict[str, Any], dir_full_path: str, backup_path: str) -> int:
    """하위 1‑계층에 존재하는 파일들의 Size 총합을 반환한다."""
    total = 0
    if not child_dict:
        return total

    for fname in child_dict.keys():
        if not fname:
            continue
        child_full_path = f"{dir_full_path}/{fname}".strip("/")
        try:
            domain, _, rel_path = child_full_path.split("/", 2)
        except ValueError:
            domain, rel_path = child_full_path, ""
        flags, blob = get_flags_and_file(backup_path, domain, rel_path)
        if flags == 1:  # File
            size_str, *_ = parse_bplist_metadata(blob)
            if size_str:
                try:
                    total += int(str(size_str).replace(",", ""))
                except ValueError:
                    pass
    return total


# ────────────────────────────────────────────────────────────────
# 5) TreeView 빌더
# ────────────────────────────────────────────────────────────────

def build_file_list_tree(
    file_list_tree: "ttk.Treeview",
    sub_dict: Dict[str, Any],
    parent: str = "",
    full_path: str = "",
    current_depth: int = 0,
    max_depth: int = 1,
    backup_path: str = "",
) -> None:
    """
    #0(text)  : 마지막 경로 요소
    values[0] : 전체 경로 (숨김)
    values[1‑] : Size / Type / mdate / cdate / perm
    """
    # Tk root 가 이미 생성된 시점 → 아이콘 준비
    _ensure_icons(file_list_tree)

    # 루트 호출 시 기존 항목 제거
    if current_depth == 0:
        for itm in file_list_tree.get_children():
            file_list_tree.delete(itm)

    if not sub_dict:
        return

    for name, child in sorted(sub_dict.items()):
        if not name:
            continue

        node_full = f"{full_path}/{name}" if full_path else name

        # Manifest.db 메타
        try:
            domain, _, rel_path = node_full.split("/", 2)
        except ValueError:
            domain, rel_path = node_full, ""
        flags, blob = get_flags_and_file(backup_path, domain, rel_path)
        size_str, mdate, cdate, perm = parse_bplist_metadata(blob)

        file_type = "Directory" if flags != 1 else "File"
        icon_key = "folder" if file_type == "Directory" else get_file_icon(name)

        # ── Directory Size 보정 (1‑계층 파일 합산) ───────────────
        if file_type == "Directory":
            agg_size = _sum_first_level_file_sizes(child, node_full, backup_path)
            if agg_size:  # 0 인 경우 표시 생략
                size_str = f"{agg_size:,}"

        values = (node_full, size_str or "", file_type, mdate, cdate, perm)
        node_id = file_list_tree.insert(
            parent,
            "end",
            text=name,
            values=values,
            image=_ICON_DICT[icon_key],
        )

        # 하위 디렉터리 재귀 (max_depth 제한)
        if isinstance(child, dict) and current_depth + 1 < max_depth:
            build_file_list_tree(
                file_list_tree,
                child,
                parent=node_id,
                full_path=node_full,
                current_depth=current_depth + 1,
                max_depth=max_depth,
                backup_path=backup_path,
            )
