from __future__ import annotations

import os
import sqlite3
import datetime as dt
import tkinter as tk
from tkinter import ttk, messagebox

from artifact_analyzer.messenger.sms.sms_analyser import IMessageAnalyzer

try:
    from PIL import Image, ImageTk  # noqa: F401
except ImportError:
    Image = ImageTk = None  # type: ignore

###############################################################################
# Helper functions                                                            #
###############################################################################

def backup_file(root: str, rel: str) -> str:
    """Return fileID from Manifest.db based on relativePath match."""

    rel = rel.lstrip("~")
    rel = rel[1:] if rel.startswith("/") else rel
    mdb = os.path.join(root, "Manifest.db")

    if os.path.exists(mdb):
        with sqlite3.connect(mdb) as conn:
            row = conn.execute(
                "SELECT fileID FROM Files WHERE relativePath=? COLLATE NOCASE LIMIT 1",
                (rel,),
            ).fetchone()
            if row:
                return row[0]  # Only return fileID if found

    return ""  # Return empty string if not found


def k_format(raw: str) -> str:
    try:
        d = dt.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return raw
    wd = ["월", "화", "수", "목", "금", "토", "일"][d.weekday()]
    ampm = "오전" if d.hour < 12 else "오후"
    h12 = d.hour if d.hour in (0, 12) else d.hour % 12
    return f"{d.year}년 {d.month}월 {d.day}일 ({wd}) {ampm} {h12}:{d.minute:02d}"

###############################################################################
# Main view                                                                   #
###############################################################################

def display_imessage(parent: tk.Misc, backup_path: str) -> None:
    # ── clear host frame ──────────────────────────────────────────────
    for w in parent.winfo_children():
        w.destroy()

    ana = IMessageAnalyzer(backup_path)
    ok, err = ana.load()
    if not ok:
        messagebox.showerror("오류", err)
        return

    # ── styles ────────────────────────────────────────────────────────
    style = ttk.Style()
    style.configure("White.TFrame", background="white")
    style.configure("Outgoing.TFrame", background="#88B6FF", relief="ridge", borderwidth=1)
    style.configure("Incoming.TFrame", background="#FFFFFF", relief="ridge", borderwidth=1)
    style.configure("CardHeader.TLabel", font=("TkDefaultFont", 12, "bold"))
    style.configure("Outgoing.TLabel", background="#88B6FF")
    style.configure("OutgoingTime.TLabel", background="#88B6FF", font=("TkDefaultFont", 8))

    # ── split view ────────────────────────────────────────────────────
    paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
    paned.pack(fill="both", expand=True)

    # ░░ chat list ░░ --------------------------------------------------
    chat_list_fr = ttk.Frame(paned)
    paned.add(chat_list_fr, weight=1)

    top_bar = ttk.Frame(chat_list_fr)
    top_bar.pack(fill="x", pady=4)
    kw = tk.StringVar()
    ttk.Label(top_bar, text="검색:").pack(side="left")
    ttk.Entry(top_bar, textvariable=kw, width=28).pack(side="left", padx=4)
    ttk.Button(top_bar, text="검색", command=lambda: _search()).pack(side="left")

    cols = ("cid", "phone", "last")
    tv = ttk.Treeview(chat_list_fr, columns=cols, show="headings", height=25)
    for c, h in zip(cols, ("ChatID", "PhoneNumber", "LastRead")):
        tv.heading(c, text=h)
    tv.column("cid", width=80, anchor="center")
    tv.column("phone", width=190)
    tv.column("last", width=160, stretch=True)
    tv.tag_configure("stripe", background="#f5f5f5")

    vsb = ttk.Scrollbar(chat_list_fr, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=vsb.set)
    tv.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    def p_disp(r):
        return r.name if (r.name and r.name != r.identifier) else r.identifier

    def _fill(rows):
        tv.delete(*tv.get_children())
        for i, r in enumerate(rows):
            tv.insert("", "end", iid=str(r.chat_id),
                     values=(r.chat_id, p_disp(r), r.last_read),
                     tags=("stripe",) if i % 2 else ())

    _fill(ana.rows)

    # ░░ chat view ░░ --------------------------------------------------
    chat_view_fr = ttk.Frame(paned, padding=8, style="White.TFrame")
    paned.add(chat_view_fr, weight=3)

    phone_lbl = ttk.Label(chat_view_fr, text="", style="CardHeader.TLabel")
    phone_lbl.pack(anchor="w", pady=(0, 4))

    canvas = tk.Canvas(chat_view_fr, highlightthickness=0, background="white")
    vbar = ttk.Scrollbar(chat_view_fr, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vbar.set)
    vbar.pack(side="right", fill="y")
    canvas.pack(fill="both", expand=True)

    msg_container = ttk.Frame(canvas, style="White.TFrame")
    canvas.create_window((0, 0), window=msg_container, anchor="nw")

    msg_container.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
    canvas.bind("<Configure>", lambda e: _sync_wrap(int(e.width * 0.9)))

    def _sync_wrap(wrap_len: int) -> None:
        for row in msg_container.winfo_children():
            for child in row.winfo_children():
                if isinstance(child, ttk.Label) and child.cget("wraplength"):
                    child.configure(wraplength=wrap_len)

    ###################################################################
    # renderer                                                         #
    ###################################################################

    def _render(cid: int, phone: str) -> None:
        phone_lbl.config(text=phone)
        for w in msg_container.winfo_children():
            w.destroy()

        wrap_len = int(canvas.winfo_width() * 0.9)

        for m in ana.get_messages(cid):
            outgoing = bool(m.get("is_from_me")) or m.get("direction") in ("발신", "outgoing", 1)
            body_text = m.get("body") or ""
            attachment_rel = (m.get("attachment") or "").replace("~/", "/")

            # ── Attachment with no rel → skip completely ─────────────────
            if not body_text and not attachment_rel.strip():
                continue

            # ── row frame & grid config ─────────────────────────────────
            row = ttk.Frame(msg_container, style="White.TFrame")
            row.pack(fill="x", pady=2, padx=4)
            if outgoing:
                row.grid_columnconfigure(0, weight=1)
                row.grid_columnconfigure(1, weight=0)
            else:
                row.grid_columnconfigure(0, weight=0)
                row.grid_columnconfigure(1, weight=1)

            sty_frame = "Outgoing.TFrame" if outgoing else "Incoming.TFrame"
            bubble = ttk.Frame(row, padding=6, style=sty_frame)
            text_style = "Outgoing.TLabel" if outgoing else "TLabel"
            time_style = "OutgoingTime.TLabel" if outgoing else "TLabel"

            # ── body / attachment text ──────────────────────────────────
            if body_text:
                ttk.Label(bubble, text=body_text, wraplength=wrap_len, justify="left", style=text_style).pack()
            else:
                fid = backup_file(backup_path, attachment_rel)
                full_path = backup_path + "/" + fid[:2]  + "/" + fid
                ext = os.path.splitext(attachment_rel)[1].lstrip(".")
                print(full_path, ext) # 해당 부분 아래를 수정해서, 이미지가 View되게 해줘
                # ── attachment renderer ────────────────────────────────────────
                if Image and ext.lower() in ("jpg", "jpeg", "png", "heic"):
                    try:
                        # HEIC는 pillow-heif(또는 pyheif) 플러그인이 있을 때만 동작
                        img = None
                        if ext.lower() == "heic":
                            try:
                                import pillow_heif  # pip install pillow-heif
                                heif = pillow_heif.read_heif(full_path)
                                img = Image.frombytes(heif.mode, heif.size, heif.data, "raw")
                            except Exception:
                                pass

                        # 나머지 확장자 또는 HEIC 플러그인 실패 시 기본 열기
                        if img is None:
                            img = Image.open(full_path)

                        # 큰 이미지는 가로 최대 300px 로 축소
                        max_w = 300
                        if img.width > max_w:
                            ratio = max_w / img.width
                            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)

                        photo = ImageTk.PhotoImage(img)

                        # 라벨에 이미지 부착 (GC 방지용으로 photo 참조 보관)
                        lbl = ttk.Label(bubble, image=photo, style=text_style)
                        lbl.image = photo
                        lbl.pack()
                    except Exception as e:
                        # 이미지 표시 실패 → 경로와 오류 텍스트로 대체
                        ttk.Label(
                            bubble,
                            text=f"{full_path} ({e})",
                            wraplength=wrap_len,
                            style=text_style,
                        ).pack()
                else:
                    # 지원하지 않는 확장자는 그냥 텍스트로 출력
                    ttk.Label(
                        bubble,
                        text=full_path,
                        wraplength=wrap_len,
                        style=text_style,
                    ).pack()

            ttk.Label(bubble, text=k_format(m["datetime"]), style=time_style).pack(anchor="e", pady=(2, 0))

            if outgoing:
                bubble.grid(row=0, column=1, sticky="e", padx=(60, 0))
            else:
                bubble.grid(row=0, column=0, sticky="w", padx=(0, 60))

        parent.after(30, lambda: canvas.yview_moveto(1.0))

    ###################################################################
    # events                                                           #
    ###################################################################

    def _search() -> None:
        k = kw.get().lower().strip()
        _fill(ana.rows if not k else ana.search(k))

    kw.trace_add("write", lambda *_: _search())

    tv.bind("<<TreeviewSelect>>", lambda _: _render(int(tv.selection()[0]), tv.item(tv.selection(), "values")[1]))
