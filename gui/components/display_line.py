# display_line.py

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, messagebox

from artifact_analyzer.messenger.line.line_analyzer import LineAnalyzer


def k_format(raw: str) -> str:
    """
    이미 문자열로 변환된 날짜(raw)를 그대로 반환합니다.
    (line_analyzer에서 format_time을 이용해 포맷함)
    """
    return raw


def display_line(parent: tk.Misc, backup_path: str) -> None:
    """
    Tkinter 기반으로 LINE 채팅방 목록과 메시지를 보여주는 UI.
    - 왼쪽: 채팅방 목록(Treeview) — UserName, LastSendTime
    - 오른쪽: 선택한 채팅방의 메시지들(캔버스에 말풍선 형태)
    """
    # ── 기존 위젯 제거 ───────────────────────────────────────────────────────
    for w in parent.winfo_children():
        w.destroy()

    # Analyzer 초기화 및 로드
    ana = LineAnalyzer(backup_path)
    ok, err = ana.load()
    if not ok:
        messagebox.showerror("오류", err)
        return

    # ── 스타일 설정 ─────────────────────────────────────────────────────────────
    style = ttk.Style()
    style.configure("White.TFrame", background="white")
    style.configure("Outgoing.TFrame", background="#DCF8C6", relief="ridge", borderwidth=1)
    style.configure("Incoming.TFrame", background="#FFFFFF", relief="ridge", borderwidth=1)
    style.configure("CardHeader.TLabel", font=("TkDefaultFont", 12, "bold"))
    style.configure("Outgoing.TLabel", background="#DCF8C6")
    style.configure("OutgoingTime.TLabel", background="#DCF8C6", font=("TkDefaultFont", 8))

    # ── 분할 뷰 ───────────────────────────────────────────────────────────────
    paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
    paned.pack(fill="both", expand=True)

    # ░░ 채팅방 리스트 영역 ░░ ------------------------------------------------
    chat_list_fr = ttk.Frame(paned)
    paned.add(chat_list_fr, weight=1)

    top_bar = ttk.Frame(chat_list_fr)
    top_bar.pack(fill="x", pady=4)
    kw = tk.StringVar()
    ttk.Label(top_bar, text="검색:").pack(side="left")
    ttk.Entry(top_bar, textvariable=kw, width=28).pack(side="left", padx=4)
    ttk.Button(top_bar, text="검색", command=lambda: _search()).pack(side="left")

    cols = ("cid", "last")
    tv = ttk.Treeview(chat_list_fr, columns=cols, show="headings", height=25)
    # 변경: ChatRoomID 대신 UserName으로 표시
    tv.heading("cid", text="UserName")
    tv.heading("last", text="LastSendTime")
    tv.column("cid", width=150, anchor="w")
    tv.column("last", width=180, stretch=True)
    tv.tag_configure("stripe", background="#f5f5f5")

    vsb = ttk.Scrollbar(chat_list_fr, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=vsb.set)
    tv.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    def _fill(rows: list[ChatRow]) -> None:
        tv.delete(*tv.get_children())
        for i, r in enumerate(rows):
            # 변경: values에 chat_id가 아닌 display_name을 넣음
            tv.insert(
                "",
                "end",
                iid=str(r.chat_id),
                values=(r.display_name, r.last_send),
                tags=("stripe",) if i % 2 else (),
            )

    _fill(ana.rows)

    # ░░ 메시지 뷰 영역 ░░ ------------------------------------------------------
    chat_view_fr = ttk.Frame(paned, padding=8, style="White.TFrame")
    paned.add(chat_view_fr, weight=3)

    header_lbl = ttk.Label(chat_view_fr, text="", style="CardHeader.TLabel")
    header_lbl.pack(anchor="w", pady=(0, 4))

    canvas = tk.Canvas(chat_view_fr, highlightthickness=0, background="white")
    vbar = ttk.Scrollbar(chat_view_fr, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vbar.set)
    vbar.pack(side="right", fill="y")
    canvas.pack(fill="both", expand=True)

    msg_container = ttk.Frame(canvas, style="White.TFrame")
    canvas.create_window((0, 0), window=msg_container, anchor="nw")

    msg_container.bind(
        "<Configure>",
        lambda _: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.bind(
        "<MouseWheel>",
        lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"),
    )
    canvas.bind(
        "<Configure>",
        lambda e: _sync_wrap(int(e.width * 0.9)),
    )

    def _sync_wrap(wrap_len: int) -> None:
        for row in msg_container.winfo_children():
            for child in row.winfo_children():
                if isinstance(child, ttk.Label) and child.cget("wraplength"):
                    child.configure(wraplength=wrap_len)

    # ── 채팅방 선택 시 메시지 렌더링 ─────────────────────────────────────────────
    def _render(cid: int) -> None:
        # 변경: ChatRoomID 대신 미리 저장해둔 display_name으로 표시
        # ana.rows에서 해당 chat_id의 display_name을 찾아옴
        selected_row = next((r for r in ana.rows if r.chat_id == cid), None)
        display_name = selected_row.display_name if selected_row else str(cid)
        header_lbl.config(text=f"{display_name}")

        for w in msg_container.winfo_children():
            w.destroy()

        wrap_len = int(canvas.winfo_width() * 0.9)
        messages = ana.get_messages(cid)

        for m in messages:
            outgoing = (m["sender_id"] == 0)
            body_text = m["message"]
            time_text = m["send_time"]

            # 빈 메시지가 있을 경우 건너뜀
            if not body_text:
                continue

            # ── 말풍선 레이아웃 ────────────────────────────────────────────
            row = ttk.Frame(msg_container, style="White.TFrame")
            row.pack(fill="x", pady=2, padx=4)
            if outgoing:
                row.grid_columnconfigure(0, weight=1)
                row.grid_columnconfigure(1, weight=0)
            else:
                row.grid_columnconfigure(0, weight=0)
                row.grid_columnconfigure(1, weight=1)

            sty_frame = "Outgoing.TFrame" if outgoing else "Incoming.TFrame"
            text_style = "Outgoing.TLabel" if outgoing else "TLabel"
            time_style = "OutgoingTime.TLabel" if outgoing else "TLabel"

            # 변경: sender_name("Me" 혹은 상대방 이름)을 제거하고, 메시지 내용(body_text)만 표시
            display_text = body_text
            ttk.Label(
                bubble := ttk.Frame(row, padding=6, style=sty_frame),
                text=display_text,
                wraplength=wrap_len,
                justify="left",
                style=text_style
            ).pack()

            # 보낸 시각
            ttk.Label(bubble, text=k_format(time_text), style=time_style).pack(anchor="e", pady=(2, 0))

            if outgoing:
                bubble.grid(row=0, column=1, sticky="e", padx=(60, 0))
            else:
                bubble.grid(row=0, column=0, sticky="w", padx=(0, 60))

        parent.after(30, lambda: canvas.yview_moveto(1.0))

    # ── 검색 기능 ────────────────────────────────────────────────────────────
    def _search() -> None:
        k = kw.get().lower().strip()
        _fill(ana.rows if not k else ana.search(k))

    kw.trace_add("write", lambda *_: _search())
    tv.bind("<<TreeviewSelect>>", lambda _: _render(int(tv.selection()[0])))
