import tkinter as tk
from tkinter import ttk, messagebox
import calendar
from datetime import datetime, timedelta
import pandas as pd

# Backend – forensic calendar DB handler
from artifact_analyzer.calendar.calendar_analyzer import CalendarAnalyser


def display_calendar(parent_frame, backup_path):
    """Interactive calendar visualiser with forensic-rich details.

    FINAL FIX APR 2025
    ------------------
    * Timeline crash resolved – participant list now expects a Python *list*,
      not a DataFrame.
    * Full code restored (no placeholders/omissions).
    """

    # ────────────────────────────────────────────────────────────────
    # 🔄  Clear previous widgets
    # ────────────────────────────────────────────────────────────────

    for w in parent_frame.winfo_children():
        w.destroy()

    # ────────────────────────────────────────────────────────────────
    # 🗃  Runtime state
    # ────────────────────────────────────────────────────────────────

    class _State:
        def __init__(self):
            now = datetime.now()
            self.year = now.year
            self.month = now.month
            self.month_events_cache: dict[str, pd.DataFrame] = {}
            self.all_events_df: pd.DataFrame | None = None

    state = _State()

    # ────────────────────────────────────────────────────────────────
    # 🎨  Styling helpers
    # ────────────────────────────────────────────────────────────────

    def _normalize_color(c: str | None) -> str:
        if not c:
            return "#FFFFFF"
        c = c.strip()
        if len(c) == 9:  # strip alpha (#RRGGBBAA → #RRGGBB)
            c = c[:7]
        return c if c.startswith("#") else f"#{c}"

    def _contrast_color(bg: str) -> str:
        try:
            bg = bg.lstrip("#")
            r, g, b = [int(bg[i : i + 2], 16) for i in (0, 2, 4)]
            return "#000000" if (r * 299 + g * 587 + b * 114) / 1000 > 128 else "#FFFFFF"
        except Exception:
            return "#000000"

    def _setup_styles():
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("HeaderLarge.TLabel", font=("Helvetica", 18, "bold"), foreground="#2C3E50")
        s.configure("Header.TLabel", font=("Helvetica", 14, "bold"), foreground="#34495E")
        s.configure("HeaderSmall.TLabel", font=("Helvetica", 10, "bold"), foreground="#2980B9")
        s.configure("Text.TLabel", font=("Helvetica", 10), foreground="#2C3E50", background="white")
        s.configure("SmallText.TLabel", font=("Helvetica", 8), foreground="#7F8C8D")
        s.configure("DayCell.TFrame", background="#FFFFFF", relief="groove", borderwidth=1)
        s.configure("WeekendCell.TFrame", background="#F8F9FA", relief="groove", borderwidth=1)
        s.configure("TodayCell.TFrame", background="#E8F4FD", relief="groove", borderwidth=1)
        s.configure("Nav.TButton", font=("Helvetica", 10), padding=5)
        s.configure("Today.TButton", font=("Helvetica", 9), padding=3)
        s.configure("Calendar.TFrame", background="#FDFDFD")
        s.configure("EventDetail.TFrame", relief="groove", borderwidth=1, padding=8)
        s.configure("ErrorText.TLabel", font=("Helvetica", 12), foreground="red")

    _setup_styles()

    # ────────────────────────────────────────────────────────────────
    # 🔌  Connect to DB
    # ────────────────────────────────────────────────────────────────

    try:
        analyser = CalendarAnalyser(backup_path)
        if not analyser.connect_to_db():
            messagebox.showerror("Error", "Calendar DB not found or could not be opened.")
            ttk.Label(parent_frame, text="DB connection failed. Check backup path.", style="ErrorText.TLabel").pack(pady=20)
            return
    except Exception as e:
        messagebox.showerror("Error", f"Failed to initialise analyser: {e}")
        ttk.Label(parent_frame, text=f"Initialisation failed: {e}", style="ErrorText.TLabel").pack(pady=20)
        return

    # ────────────────────────────────────────────────────────────────
    # 🔍  Data fetch helpers
    # ────────────────────────────────────────────────────────────────

    def _fetch_participants(event_id: int) -> list[dict]:
        try:
            return analyser.get_participants(event_id) or []
        except Exception:
            return []

    def _fetch_alarms(event_id: int) -> list[dict]:
        try:
            return analyser.get_alarms_for_event(event_id) or []
        except Exception:
            return []

    def _fetch_location_details(loc_id: int | None) -> list[dict]:
        if not loc_id:
            return []
        try:
            return analyser.get_location_info(loc_id) or []
        except Exception:
            return []

    # ────────────────────────────────────────────────────────────────
    # 🛠  Formatting helpers
    # ────────────────────────────────────────────────────────────────

    _role_map = {"ORGANIZER": "Organizer", "ATTENDEE": "Attendee", "OPTIONAL": "Optional"}
    _status_map = {
        "ACCEPTED": "Accepted",
        "DECLINED": "Declined",
        "TENTATIVE": "Tentative",
        "NEEDS-ACTION": "Needs Action",
    }

    def _participants_as_text(parts: list[dict]) -> str:
        out: list[str] = []
        for p in parts:
            email = p.get("email", "")
            name = p.get("name", "")
            role = _role_map.get(p.get("role", ""), p.get("role", ""))
            status = _status_map.get(p.get("status", ""), p.get("status", ""))
            s = f"{name} <{email}>" if name else email
            if role:
                s += f" ({role}"
                if status:
                    s += f", {status}"
                s += ")"
            out.append(s)
        return ", ".join(out)

    def _alarms_as_text(alarms: list[dict]) -> str:
        out: list[str] = []
        for a in alarms:
            trg = a.get("trigger_date", "")
            a_type = a.get("type", "")
            if isinstance(trg, int):
                minutes = abs(trg)
                hrs, mins = divmod(minutes, 60)
                pretty = f"{hrs}h {mins}m" if hrs else f"{minutes}m"
                trg_txt = f"{pretty} {'before' if trg < 0 else 'after'} event"
            else:
                trg_txt = str(trg)
            out.append(f"{a_type}: {trg_txt}" if a_type else trg_txt)
        return ", ".join(out)

    # ────────────────────────────────────────────────────────────────
    # 💬  Tooltip helper
    # ────────────────────────────────────────────────────────────────

    def _tooltip(widget: tk.Widget, text: str):
        tip = None

        def _enter(_):
            nonlocal tip
            if tip or not text:
                return
            x, y, *_ = widget.bbox("insert") or (0, 0, 0, 0)
            x += widget.winfo_rootx() + 20
            y += widget.winfo_rooty() + 20
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            ttk.Label(tip, text=text, background="#FFFFE0", relief="solid", borderwidth=1, padding=(5, 3)).pack()

        def _leave(_):
            nonlocal tip
            if tip:
                tip.destroy()
                tip = None

        widget.bind("<Enter>", _enter)
        widget.bind("<Leave>", _leave)

    # ────────────────────────────────────────────────────────────────
    # 🏗  Event detail builder
    # ────────────────────────────────────────────────────────────────

    def _build_event_detail(parent: ttk.Frame, ev: pd.Series | dict):
        frm = ttk.Frame(parent, style="EventDetail.TFrame")
        frm.pack(fill="x", pady=8)

        # ‑‑ header (title & time) ‑‑
        hdr = ttk.Frame(frm)
        hdr.pack(fill="x", pady=(0, 4))
        color = ev.get("color", "")
        if color:
            tk.Frame(hdr, width=16, height=16, bg=_normalize_color(color)).pack(side="left", padx=(0, 6))
        ttk.Label(hdr, text=ev.get("summary") or "Untitled", style="Header.TLabel").pack(side="left")

        s_dt, e_dt = ev.get("start_date"), ev.get("end_date")
        all_day = ev.get("all_day", False)
        if s_dt:
            time_txt = "All day" if all_day else s_dt.strftime("%H:%M")
            if e_dt and e_dt != s_dt:
                if all_day:
                    time_txt += f" ({s_dt.strftime('%Y-%m-%d')} ~ {e_dt.strftime('%Y-%m-%d')})"
                else:
                    fmt = "%H:%M" if s_dt.date() == e_dt.date() else "%Y-%m-%d %H:%M"
                    time_txt += f" ~ {e_dt.strftime(fmt)}"
            ttk.Label(hdr, text=f"({time_txt})", style="SmallText.TLabel").pack(side="right")

        # ‑‑ main property table ‑‑
        props_tree = ttk.Treeview(frm, columns=("field", "val"), show="headings", height=6, style="Detail.Treeview")
        props_tree.heading("field", text="Field")
        props_tree.heading("val", text="Value")
        props_tree.column("field", width=120, anchor="w")
        props_tree.column("val", width=480, anchor="w")
        props_tree.pack(fill="x", expand=True)

        def _add(k: str, v: str | None):
            if v:
                props_tree.insert("", "end", values=(k, v))

        _add("Calendar", ev.get("calendar_title", ""))
        if color and ev.get("symbolic_color_name"):
            _add("Color", f"{ev.get('symbolic_color_name')} ({color})")
        _add("Location", ev.get("location", ""))
        _add("Description", ev.get("description", ""))
        _add("Participants", _participants_as_text(_fetch_participants(int(ev["event_id"])) if "event_id" in ev else []))
        _add("Alarms", _alarms_as_text(_fetch_alarms(int(ev["event_id"])) if "event_id" in ev else []))

        # zebra strip rows manually (since ttk.Treeview lacks style per‑row)
        for i, iid in enumerate(props_tree.get_children()):
            props_tree.tag_configure("odd", background="#f9f9f9")
            if i % 2:
                props_tree.item(iid, tags=("odd",))

        # ‑‑ location details table ‑‑
        loc_details = _fetch_location_details(ev.get("location_id"))
        if loc_details:
            loc_lbl = ttk.Label(frm, text="Location Details", style="HeaderSmall.TLabel")
            loc_lbl.pack(anchor="w", pady=(8, 0))
            loc_tree = ttk.Treeview(frm, columns=("k", "v"), show="headings", height=len(loc_details), style="Detail.Treeview")
            loc_tree.heading("k", text="Key")
            loc_tree.heading("v", text="Value")
            loc_tree.column("k", width=120, anchor="w")
            loc_tree.column("v", width=480, anchor="w")
            loc_tree.pack(fill="x", expand=True)
            for loc in loc_details:
                if loc.get("title"):
                    loc_tree.insert("", "end", values=("Name", loc["title"]))
                if loc.get("address"):
                    loc_tree.insert("", "end", values=("Address", loc["address"]))
                lat, lng = loc.get("latitude"), loc.get("longitude")
                if lat and lng:
                    loc_tree.insert("", "end", values=("Coords", f"{lat}, {lng}"))
            for i, iid in enumerate(loc_tree.get_children()):
                if i % 2:
                    loc_tree.item(iid, tags=("odd",))

    # ────────────────────────────────────────────────────────────────
    # 🗄  Data loaders
    # ────────────────────────────────────────────────────────────────

    def _load_month_events() -> dict[int, list[dict]]:
        key = f"{state.year}-{state.month}"
        if key not in state.month_events_cache:
            state.month_events_cache[key] = analyser.get_events_for_month(state.year, state.month)
        df = state.month_events_cache[key]
        out: dict[int, list[dict]] = {}
        for _, ev in df.iterrows():
            s: datetime | None = ev["start_date"]
            e: datetime | None = ev.get("end_date") or s
            if s is None:
                continue
            d = s.date()
            while d <= e.date():
                if d.month == state.month and d.year == state.year:
                    out.setdefault(d.day, []).append(ev)
                d += timedelta(days=1)
        return out

    def _load_all_events() -> pd.DataFrame:
        if state.all_events_df is not None:
            return state.all_events_df
        q = """
        SELECT ci.ROWID AS event_id,
               ci.summary,
               ci.description,
               ci.location_id,
               ci.start_date,
               ci.end_date,
               ci.all_day,
               c.title  AS calendar_title,
               c.color,
               c.symbolic_color_name,
               l.title  AS location
        FROM   CalendarItem ci
               LEFT JOIN Calendar c ON ci.calendar_id = c.ROWID
               LEFT JOIN Location l ON ci.location_id = l.ROWID
        ORDER  BY ci.start_date;
        """
        df = pd.read_sql_query(q, analyser.conn)
        df["start_date"] = df["start_date"].apply(analyser._convert_date)
        df["end_date"] = df["end_date"].apply(analyser._convert_date)
        state.all_events_df = df
        return df

    # ────────────────────────────────────────────────────────────────
    # 🔍  Event-level detail window
    # ────────────────────────────────────────────────────────────────

    def _show_event_detail(ev: pd.Series | dict):
        win = tk.Toplevel(parent_frame)
        win.title(ev.get("summary") or "Event Details")
        win.geometry("720x520")
        win.transient(parent_frame)
        win.grab_set()

        canvas = tk.Canvas(win, highlightthickness=0)
        sb = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = ttk.Frame(canvas, padding=10)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def _sync_width(e):
            canvas.itemconfigure(window_id, width=e.width)
        canvas.bind("<Configure>", _sync_width)
        content.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))

        _build_event_detail(content, ev)
        ttk.Label(content).pack(pady=4)

    # ────────────────────────────────────────────────────────────────
    # 📆  Calendar header/nav
    # ────────────────────────────────────────────────────────────────

    ttk.Label(parent_frame, text="Calendar Viewer", style="HeaderLarge.TLabel").pack(anchor="w", pady=(0, 5))

    nav = ttk.Frame(parent_frame)
    nav.pack(fill="x", pady=5)

    ttk.Button(nav, text="◀ Prev", style="Nav.TButton", command=lambda: _change_month(-1)).pack(side="left")

    month_var = tk.StringVar()

    def _update_month_label():
        month_var.set(f"{calendar.month_name[state.month]} {state.year}")

    ttk.Label(nav, textvariable=month_var, style="Header.TLabel", width=14, anchor="center").pack(side="left", padx=12)

    ttk.Button(nav, text="Next ▶", style="Nav.TButton", command=lambda: _change_month(1)).pack(side="left")
    ttk.Button(nav, text="Today", style="Today.TButton", command=lambda: _go_today()).pack(side="right", padx=5)
    ttk.Button(nav, text="Timeline", style="Nav.TButton", command=lambda: _show_timeline()).pack(side="right", padx=5)

    # ────────────────────────────────────────────────────────────────
    # 📆  Calendar grid
    # ────────────────────────────────────────────────────────────────

    cal_frame = ttk.Frame(parent_frame, style="Calendar.TFrame")
    cal_frame.pack(fill="both", expand=True, pady=10)

    cal_frame.rowconfigure(0, weight=0)
    for r in range(1, 7):
        cal_frame.rowconfigure(r, weight=1, uniform="day")
    for c in range(7):
        cal_frame.columnconfigure(c, weight=1, uniform="day")

    # --------------------------------------------------------------
    # 🔄  Calendar refresh
    # --------------------------------------------------------------

    def _refresh():
        for w in cal_frame.winfo_children():
            w.destroy()
        ev_by_day = _load_month_events()

        # weekday headers
        for c, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            ttk.Label(cal_frame, text=name, style="HeaderSmall.TLabel", anchor="center").grid(row=0, column=c, sticky="nsew", padx=2, pady=2)

        today = datetime.now().date()
        for r, week in enumerate(calendar.Calendar(firstweekday=0).monthdayscalendar(state.year, state.month), start=1):
            for c, day in enumerate(week):
                if day == 0:
                    ttk.Frame(cal_frame).grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
                    continue
                style = "WeekendCell.TFrame" if c >= 5 else "DayCell.TFrame"
                if day == today.day and state.month == today.month and state.year == today.year:
                    style = "TodayCell.TFrame"
                cell = ttk.Frame(cal_frame, style=style)
                cell.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)

                ttk.Label(cell, text=str(day), style="Header.TLabel", anchor="nw").pack(anchor="nw", padx=2, pady=2)
                if day in ev_by_day:
                    events = ev_by_day[day]
                    for ev in events[:3]:
                        title = ev.get("summary") or "Untitled"
                        bg = _normalize_color(ev.get("color"))
                        fg = _contrast_color(bg)
                        lbl = tk.Label(cell, text=title, bg=bg, fg=fg, font=("Helvetica", 9), anchor="w", relief="groove", padx=3, pady=1)
                        lbl.pack(fill="x", padx=2, pady=1)
                        lbl.bind("<Double-1>", lambda e, ev_data=ev: _show_event_detail(ev_data))
                        _tooltip(lbl, title)
                    if len(events) > 3:
                        more_lbl = ttk.Label(cell, text=f"+ {len(events)-3} more…", style="SmallText.TLabel")
                        more_lbl.pack(anchor="e", padx=2)
                        more_lbl.bind("<Button-1>", lambda e, d=day: _show_day_details(d))
                cell.bind("<Double-1>", lambda e, d=day: _show_day_details(d))

    # --------------------------------------------------------------
    # 📜  Timeline view (fixed)
    # --------------------------------------------------------------

    def _show_timeline():
        df = _load_all_events()
        if df.empty:
            messagebox.showinfo("Timeline", "No events found in backup.")
            return

        win = tk.Toplevel(parent_frame)
        win.title("Timeline – All Events")
        win.geometry("1080x600")
        win.transient(parent_frame)
        win.grab_set()

        cols = ("Start", "End", "Title", "Calendar", "Location", "Participants", "Description")
        widths = {"Start": 150, "End": 150, "Title": 220, "Calendar": 140, "Location": 140, "Participants": 200, "Description": 300}

        container = ttk.Frame(win)
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        tree = ttk.Treeview(container, columns=cols, show="headings", height=25)
        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=widths[col], anchor="w" if col not in ("Start", "End") else "center")

        for _, row in df.iterrows():
            s = row["start_date"].strftime("%Y-%m-%d %H:%M") if pd.notna(row["start_date"]) else "—"
            e = row["end_date"].strftime("%Y-%m-%d %H:%M") if pd.notna(row["end_date"]) else "—"
            title = row.get("summary") or "Untitled"
            cal_title = row.get("calendar_title") or ""
            loc = row.get("location") or ""
            desc = (row.get("description") or "").replace("\n", " ")
            desc = desc if len(desc) <= 120 else desc[:117] + "…"

            parts = _participants_as_text(_fetch_participants(int(row["event_id"])))
            if len(parts) > 80:
                parts = parts[:77] + "…"

            tree.insert("", "end", values=(s, e, title, cal_title, loc, parts, desc), tags=(str(row["event_id"]),))

        def _on_dbl(e: tk.Event):
            iid = tree.identify_row(e.y)
            if not iid:
                return
            event_id = int(tree.item(iid, "tags")[0])
            row = df[df.event_id == event_id].iloc[0]
            _show_event_detail(row)

        tree.bind("<Double-1>", _on_dbl)

    # --------------------------------------------------------------
    # 🔎  Day detail popup
    # --------------------------------------------------------------

    def _show_day_details(day: int):
        evs = _load_month_events().get(day)
        if not evs:
            return

        win = tk.Toplevel(parent_frame)
        win.title(f"{calendar.month_name[state.month]} {day}, {state.year}")
        win.geometry("820x560")
        win.transient(parent_frame)
        win.grab_set()

        hdr = ttk.Frame(win, padding=5)
        hdr.pack(fill="x")
        ttk.Label(hdr, text=datetime(state.year, state.month, day).strftime("%A, %B %d, %Y"), style="HeaderLarge.TLabel").pack(side="left")
        ttk.Button(hdr, text="Close", command=win.destroy).pack(side="right")
        ttk.Separator(win, orient="horizontal").pack(fill="x", pady=4)

        canvas = tk.Canvas(win, highlightthickness=0)
        sb = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = ttk.Frame(canvas, padding=10)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def _sync_width(e):
            canvas.itemconfigure(window_id, width=e.width)
        canvas.bind("<Configure>", _sync_width)
        content.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))

        for ev in sorted(evs, key=lambda x: x.get("start_date") or datetime.max):
            _build_event_detail(content, ev)

        ttk.Label(content).pack(pady=4)

    # --------------------------------------------------------------
    # 🧭  Navigation helpers
    # --------------------------------------------------------------

    def _goto_date_and_show(y: int, m: int, d: int):
        state.year, state.month = y, m
        _update_month_label()
        _refresh()
        _show_day_details(d)

    def _go_today():
        now = datetime.now()
        state.year, state.month = now.year, now.month
        _update_month_label()
        _refresh()

    def _change_month(delta: int):
        m = state.month + delta
        y = state.year
        if m < 1:
            m, y = 12, y - 1
        elif m > 12:
            m, y = 1, y + 1
        state.month, state.year = m, y
        _update_month_label()
        _refresh()

    # --------------------------------------------------------------
    # 🚀  Initial paint
    # --------------------------------------------------------------

    _update_month_label()
    _refresh()

    status = ttk.Frame(parent_frame)
    status.pack(fill="x", pady=5)
    ttk.Label(status, text=f"Backup path: {backup_path}", style="SmallText.TLabel").pack(side="right")
    