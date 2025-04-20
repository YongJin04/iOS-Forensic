import tkinter as tk
from tkinter import ttk, messagebox
import calendar
from datetime import datetime, timedelta
import pandas as pd
from functools import partial

# Backend module import (forensic functionality integrated CalendarAnalyser)
from artifact_analyzer.calendar.calendar_analyzer import CalendarAnalyser


def display_calendar(parent_frame, backup_path):
    """
    Responsive calendar UI that scales evenly within the parent_frame.

    Highlights
    ----------
    * Grid layout with uniform row/column sizes (every day cell has the same size)
    * Supports multi‑day events automatically
    * Double‑click to open a scrollable, detailed pop‑up for the selected day
    * Lazy loading and caching for performance
    """

    # Clear any existing widgets in the parent (memory‑friendly)
    for widget in parent_frame.winfo_children():
        widget.destroy()

    # ---------------- State Container ----------------

    class CalendarState:
        def __init__(self):
            self.current_date = datetime.now()
            self.current_year = self.current_date.year
            self.current_month = self.current_date.month
            self.events_cache = {}  # {"YYYY-M": events_df}

    state = CalendarState()

    # ---------------- Utility functions ----------------

    def normalize_color(color_str):
        """Return a #RRGGBB string (strip alpha channel if present)."""
        if isinstance(color_str, str) and len(color_str) == 9:
            return color_str[:7]
        return color_str or "#FFFFFF"

    def create_tooltip(widget, text):
        """Attach a simple tooltip to ``widget``."""
        tooltip = None

        def enter(event):
            nonlocal tooltip
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            label = ttk.Label(tooltip, text=text, background="lightyellow",
                              relief="solid", borderwidth=1, padding=(5, 3))
            label.pack()

        def leave(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None

        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    # ---------------- Styling ----------------

    def setup_styles():
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("HeaderLarge.TLabel", font=("Helvetica", 18, "bold"), foreground="#2C3E50")
        style.configure("Header.TLabel", font=("Helvetica", 14, "bold"), foreground="#34495E")
        style.configure("HeaderSmall.TLabel", font=("Helvetica", 10, "bold"), foreground="#2980B9")
        style.configure("Text.TLabel", font=("Helvetica", 10), foreground="#2C3E50", background="white")
        style.configure("SmallText.TLabel", font=("Helvetica", 8), foreground="#7F8C8D")
        style.configure("DayCell.TFrame", background="#FFFFFF", relief="groove", borderwidth=1)
        style.configure("WeekendCell.TFrame", background="#F8F9FA", relief="groove", borderwidth=1)
        style.configure("TodayCell.TFrame", background="#E8F4FD", relief="groove", borderwidth=1)
        style.configure("Event.TLabel", font=("Helvetica", 9), background="#3498DB", foreground="white")
        style.configure("Nav.TButton", font=("Helvetica", 10), padding=5)
        style.configure("Today.TButton", font=("Helvetica", 9), padding=3)
        style.configure("Calendar.TFrame", background="#FDFDFD")
        style.configure("EventDetail.TFrame", relief="groove", borderwidth=1, padding=8)
        style.configure("ErrorText.TLabel", font=("Helvetica", 12), foreground="red")

    setup_styles()

    # ---------------- Calendar analyser ----------------

    try:
        cal_analyser = CalendarAnalyser(backup_path)
        if not cal_analyser.connect_to_db():
            messagebox.showerror("Error", "Calendar DB not found or could not be opened.")
            ttk.Label(parent_frame, text="DB connection failed. Check the backup path.",
                      style="ErrorText.TLabel").pack(pady=20)
            return
    except Exception as e:
        messagebox.showerror("Error", f"Failed to initialise analyser: {str(e)}")
        ttk.Label(parent_frame, text=f"Initialisation failed: {str(e)}",
                  style="ErrorText.TLabel").pack(pady=20)
        return

    # ---------------- Header / Navigation ----------------

    header_frame = ttk.Frame(parent_frame)
    header_frame.pack(fill="x", pady=(0, 5))
    header_label = ttk.Label(header_frame, text="Calendar Viewer", style="HeaderLarge.TLabel")
    header_label.pack(side="left", pady=(0, 5))

    month_label_var = tk.StringVar()

    def update_month_label():
        month_label_var.set(f"{calendar.month_name[state.current_month]} {state.current_year}")

    update_month_label()

    nav_frame = ttk.Frame(parent_frame)
    nav_frame.pack(fill="x", pady=5)

    prev_month_btn = ttk.Button(nav_frame, text="◀ Prev",
                                command=lambda: change_month(-1),
                                style="Nav.TButton")
    prev_month_btn.pack(side="left")
    create_tooltip(prev_month_btn, "Previous month")

    # ─── 여기부터 수정 ───
    # width=14: 'September 2025' (9글자+1공백+4숫자 = 14글자) 폭만큼 고정
    month_label = ttk.Label(nav_frame,
                            textvariable=month_label_var,
                            style="Header.TLabel",
                            width=14,
                            anchor="center")
    month_label.pack(side="left", padx=10)
    # ────────────────────

    next_month_btn = ttk.Button(nav_frame, text="Next ▶",
                                command=lambda: change_month(1),
                                style="Nav.TButton")
    next_month_btn.pack(side="left")
    create_tooltip(next_month_btn, "Next month")

    today_btn = ttk.Button(nav_frame, text="Today",
                           command=lambda: go_to_today(),
                           style="Today.TButton")
    today_btn.pack(side="right", padx=5)
    create_tooltip(today_btn, "Go to today")

    # ---------------- Main calendar frame ----------------

    calendar_frame = ttk.Frame(parent_frame, style="Calendar.TFrame")
    calendar_frame.pack(fill="both", expand=True, pady=10)

    # Uniform cell sizes – header row (0) excluded from uniform group
    calendar_frame.rowconfigure(0, weight=0)
    for r in range(1, 7):
        calendar_frame.rowconfigure(r, weight=1, uniform="day")
    for c in range(7):
        calendar_frame.columnconfigure(c, weight=1, uniform="day")

    # ---------------- Data helpers ----------------

    def load_events():
        cache_key = f"{state.current_year}-{state.current_month}"
        if cache_key in state.events_cache:
            events_df = state.events_cache[cache_key]
        else:
            events_df = cal_analyser.get_events_for_month(state.current_year, state.current_month)
            state.events_cache[cache_key] = events_df

        events_by_day = {}
        for _, event in events_df.iterrows():
            start_dt = event["start_date"]
            end_dt = event.get("end_date") or start_dt
            if not start_dt:
                continue
            curr = start_dt.date()
            end_day = end_dt.date() if end_dt else curr
            while curr <= end_day:
                if curr.month == state.current_month and curr.year == state.current_year:
                    day_num = curr.day
                    events_by_day.setdefault(day_num, [])
                    eid = event.get("event_id")
                    if not any(e.get("event_id") == eid for e in events_by_day[day_num]):
                        events_by_day[day_num].append(event)
                curr += timedelta(days=1)
        return events_by_day

    def refresh_calendar():
        for widget in calendar_frame.winfo_children():
            widget.destroy()
        events_by_day = load_events()
        days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for col, name in enumerate(days_of_week):
            ttk.Label(calendar_frame, text=name, style="HeaderSmall.TLabel", anchor="center")\
                .grid(row=0, column=col, sticky="nsew", padx=2, pady=2)

        today = datetime.now().date()
        cal_obj = calendar.Calendar(firstweekday=0)
        month_weeks = cal_obj.monthdayscalendar(state.current_year, state.current_month)

        for row_idx, week in enumerate(month_weeks, start=1):
            for col_idx, day_num in enumerate(week):
                if day_num == 0:
                    ttk.Frame(calendar_frame).grid(row=row_idx, column=col_idx, sticky="nsew", padx=2, pady=2)
                    continue
                cell_style = "WeekendCell.TFrame" if col_idx >= 5 else "DayCell.TFrame"
                if (day_num == today.day and state.current_month == today.month and
                        state.current_year == today.year):
                    cell_style = "TodayCell.TFrame"
                cell_frame = ttk.Frame(calendar_frame, style=cell_style)
                cell_frame.grid(row=row_idx, column=col_idx, sticky="nsew", padx=2, pady=2)

                lbl_day = ttk.Label(cell_frame, text=str(day_num), style="Header.TLabel", anchor="nw")
                lbl_day.pack(anchor="nw", padx=2, pady=2)

                if day_num in events_by_day:
                    events = events_by_day[day_num]
                    max_visible = 3
                    show_more = len(events) > max_visible
                    visible = events[:max_visible]
                    for ev in visible:
                        summary = ev.get("summary") or "Untitled"
                        bg = normalize_color(ev.get("color"))
                        fg = get_contrast_color(bg)
                        ev_label = tk.Label(cell_frame, text=summary, bg=bg, fg=fg,
                                            font=("Helvetica", 9), anchor="w", relief="groove", padx=3, pady=1)
                        ev_label.pack(fill="x", padx=2, pady=1)
                        start_dt = ev.get("start_date")
                        end_dt = ev.get("end_date")
                        time_str = ""
                        if start_dt:
                            time_str = start_dt.strftime("%H:%M")
                            if end_dt and end_dt != start_dt:
                                time_str += f" ~ {end_dt.strftime('%H:%M')}"
                        tt_text = f"{summary}\n{time_str}\n{ev.get('calendar_title', '')}"
                        create_tooltip(ev_label, tt_text)
                        ev_label.bind("<Double-1>", lambda e, d=day_num: show_day_details(d))
                    if show_more:
                        more_cnt = len(events) - max_visible
                        more_label = ttk.Label(cell_frame, text=f"+ {more_cnt} more...", style="SmallText.TLabel")
                        more_label.pack(anchor="e", padx=2)
                        more_label.bind("<Button-1>", lambda e, d=day_num: show_day_details(d))

                def on_day_click(e, day=day_num):
                    show_day_details(day)

                cell_frame.bind("<Double-1>", on_day_click)
                lbl_day.bind("<Double-1>", on_day_click)

    def get_contrast_color(bg):
        try:
            bg = bg.lstrip('#')
            if len(bg) != 6:
                return "#000000"
            r, g, b = int(bg[:2], 16), int(bg[2:4], 16), int(bg[4:], 16)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return "#000000" if brightness > 128 else "#FFFFFF"
        except Exception:
            return "#000000"

    def show_day_details(day):
        detail_window = tk.Toplevel(parent_frame)
        detail_window.title(f"Events on {calendar.month_name[state.current_month]} {day}, {state.current_year}")
        detail_window.geometry("750x550")
        detail_window.transient(parent_frame)
        detail_window.grab_set()

        header_frame = ttk.Frame(detail_window, padding=5)
        header_frame.pack(fill="x", pady=(5, 0))
        header_date = datetime(state.current_year, state.current_month, day).strftime("%A, %B %d, %Y")
        ttk.Label(header_frame, text=header_date, style="HeaderLarge.TLabel").pack(side="left")
        ttk.Button(header_frame, text="Close", command=detail_window.destroy).pack(side="right")
        ttk.Separator(detail_window, orient="horizontal").pack(fill="x", pady=5)

        canvas = tk.Canvas(detail_window, highlightthickness=0)
        scrollbar = ttk.Scrollbar(detail_window, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        content_frame = ttk.Frame(canvas, padding=10)
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")
        content_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _wheel)

        def on_close():
            canvas.unbind_all("<MouseWheel>")
            detail_window.destroy()
        detail_window.protocol("WM_DELETE_WINDOW", on_close)

        events_by_day = load_events()
        events = events_by_day.get(day, [])
        if not events:
            ttk.Label(content_frame, text="No events on this date.", style="Text.TLabel", font=("Helvetica", 12))\
                .pack(pady=20)
            return

        sorted_events = sorted(events, key=lambda e: e.get("start_date", datetime.max))
        for i, event in enumerate(sorted_events):
            evt_frame = ttk.Frame(content_frame, style="EventDetail.TFrame")
            evt_frame.pack(fill="x", pady=4)

            event_id = event.get("event_id", "")
            summary = event.get("summary") or "Untitled"
            calendar_title = event.get("calendar_title", "")
            description = event.get("description", "")
            location = event.get("location", "")
            color = event.get("color", "")
            symbolic_color = event.get("symbolic_color_name", "")
            is_all_day = event.get("all_day", False)

            start_dt = event.get("start_date")
            end_dt = event.get("end_date")
            start_str = start_dt.strftime("%Y-%m-%d %H:%M") if start_dt else "No date"
            if is_all_day:
                time_str = "All day"
                if end_dt and end_dt.date() != start_dt.date():
                    time_str += f" ({start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')})"
            else:
                time_str = start_str
                if end_dt:
                    if start_dt.date() == end_dt.date():
                        time_str += f" ~ {end_dt.strftime('%H:%M')}"
                    else:
                        time_str += f" ~ {end_dt.strftime('%Y-%m-%d %H:%M')}"

            header_f = ttk.Frame(evt_frame)
            header_f.pack(fill="x", expand=True)
            if color:
                tk.Frame(header_f, width=16, height=16, bg=normalize_color(color)).pack(side="left", padx=(0, 5))
            ttk.Label(header_f, text=summary, style="Header.TLabel").pack(side="left")
            ttk.Label(header_f, text=f"({time_str})", style="SmallText.TLabel").pack(side="right")

            info_f = ttk.Frame(evt_frame)
            info_f.pack(fill="x", pady=5)
            info_f.columnconfigure(0, weight=0)
            info_f.columnconfigure(1, weight=1)

            def add_info(r, label, val, tooltip=None):
                if not val:
                    return r
                ttk.Label(info_f, text=label + ":", style="HeaderSmall.TLabel").grid(row=r, column=0, sticky="w",
                                                                                    padx=(0, 10), pady=2)
                v = ttk.Label(info_f, text=str(val), style="Text.TLabel", wraplength=650)
                v.grid(row=r, column=1, sticky="w", pady=2)
                if tooltip:
                    create_tooltip(v, tooltip)
                return r + 1

            row = 0
            if calendar_title:
                row = add_info(row, "Calendar", calendar_title)
            if color and symbolic_color:
                row = add_info(row, "Color", f"{symbolic_color} ({color})")
            if location:
                row = add_info(row, "Location", location)
            if description:
                row = add_info(row, "Description", description)

            if event_id:
                forensic_frame = ttk.Frame(evt_frame)
                forensic_frame.pack(fill="x", pady=5)
                ttk.Label(forensic_frame, text="Forensic Details", style="HeaderSmall.TLabel")\
                    .pack(anchor="w", pady=(5, 3))
                ttk.Separator(forensic_frame, orient="horizontal").pack(fill="x", pady=2)
                forensic_content = ttk.Frame(forensic_frame)
                forensic_content.pack(fill="x", pady=3)

                errors = cal_analyser.get_error_logs(event_id)
                if errors:
                    err_f = ttk.LabelFrame(forensic_content, text="Error Log")
                    err_f.pack(fill="x", pady=3)
                    for err in errors:
                        err_type = err.get('error_type', '')
                        err_code = err.get('error_code', '')
                        user_info = err.get('user_info', '')
                        timestamp = err.get('timestamp', '')
                        txt = f"{err_type}: {err_code}"
                        if user_info:
                            txt += f" ({user_info})"
                        if timestamp:
                            txt += f" - {timestamp}"
                        ttk.Label(err_f, text=txt, style="SmallText.TLabel").pack(anchor="w", padx=5)

                actions = cal_analyser.get_event_actions(event_id)
                if actions:
                    act_f = ttk.LabelFrame(forensic_content, text="External Sync")
                    act_f.pack(fill="x", pady=3)
                    for act in actions:
                        ext_id = act.get('external_id', '')
                        ext_tag = act.get('external_mod_tag', '')
                        txt = f"ID: {ext_id}"
                        if ext_tag:
                            txt += f", Tag: {ext_tag}"
                        ttk.Label(act_f, text=txt, style="SmallText.TLabel").pack(anchor="w", padx=5)

                recurrences = cal_analyser.get_recurrence_info(event_id)
                if recurrences:
                    rec_f = ttk.LabelFrame(forensic_content, text="Recurrence Rules")
                    rec_f.pack(fill="x", pady=3)
                    freq_map = {'DAILY': 'Daily', 'WEEKLY': 'Weekly', 'MONTHLY': 'Monthly', 'YEARLY': 'Yearly'}
                    for rec in recurrences:
                        freq = freq_map.get(rec.get('frequency', ''), rec.get('frequency', ''))
                        interval = rec.get('interval', '')
                        until = rec.get('until_date', '')
                        count = rec.get('count', '')
                        txt = f"{freq}"
                        if interval and interval != '1':
                            txt += f" every {interval}"
                        if until:
                            txt += f", until: {until}"
                        elif count:
                            txt += f", {count} times"
                        ttk.Label(rec_f, text=txt, style="SmallText.TLabel").pack(anchor="w", padx=5)
                    exceptions = cal_analyser.get_exception_dates(event_id)
                    if exceptions:
                        ttk.Label(rec_f, text="Exceptions:", style="SmallText.TLabel").pack(anchor="w", padx=5,
                                                                                           pady=(5, 0))
                        exc_dates = [exc.get('date').strftime('%Y-%m-%d') if isinstance(exc.get('date'), datetime)
                                     else str(exc.get('date')) for exc in exceptions]
                        ttk.Label(rec_f, text=", ".join(exc_dates), style="SmallText.TLabel", wraplength=650)\
                            .pack(anchor="w", padx=15)

                participants = cal_analyser.get_participants(event_id)
                if participants:
                    part_f = ttk.LabelFrame(forensic_content, text="Participants")
                    part_f.pack(fill="x", pady=3)
                    role_map = {'ORGANIZER': 'Organizer', 'ATTENDEE': 'Attendee', 'OPTIONAL': 'Optional'}
                    status_map = {'ACCEPTED': 'Accepted', 'DECLINED': 'Declined', 'TENTATIVE': 'Tentative',
                                  'NEEDS-ACTION': 'Needs Action'}
                    for p in participants:
                        email = p.get('email', '')
                        name = p.get('name', '')
                        role = role_map.get(p.get('role', ''), p.get('role', ''))
                        status = status_map.get(p.get('status', ''), p.get('status', ''))
                        txt = f"{name} <{email}>" if name else email
                        if role:
                            txt += f" ({role}"
                            if status:
                                txt += f", {status}"
                            txt += ")"
                        ttk.Label(part_f, text=txt, style="SmallText.TLabel").pack(anchor="w", padx=5)

                loc_id = event.get('location_id')
                if loc_id:
                    loc_info = cal_analyser.get_location_info(loc_id)
                    if loc_info:
                        loc_f = ttk.LabelFrame(forensic_content, text="Location Details")
                        loc_f.pack(fill="x", pady=3)
                        for loc in loc_info:
                            title = loc.get('title', '')
                            address = loc.get('address', '')
                            lat = loc.get('latitude', '')
                            lng = loc.get('longitude', '')
                            if title:
                                ttk.Label(loc_f, text=f"Name: {title}", style="SmallText.TLabel").pack(anchor="w", padx=5)
                            if address:
                                ttk.Label(loc_f, text=f"Address: {address}", style="SmallText.TLabel")\
                                    .pack(anchor="w", padx=5)
                            if lat and lng:
                                ttk.Label(loc_f, text=f"Coords: {lat}, {lng}", style="SmallText.TLabel")\
                                    .pack(anchor="w", padx=5)

                alarms = cal_analyser.get_alarms_for_event(event_id)
                if alarms:
                    alarm_f = ttk.LabelFrame(forensic_content, text="Alarms")
                    alarm_f.pack(fill="x", pady=3)
                    for alarm in alarms:
                        trigger = alarm.get('trigger_date', '')
                        alarm_type = alarm.get('type', '')
                        trigger_txt = str(trigger)
                        if isinstance(trigger, int):
                            minutes = abs(trigger)
                            hours, mins = divmod(minutes, 60)
                            pretty = f"{hours}h {mins}m" if hours else f"{minutes}m"
                            trigger_txt = f"{pretty} {'before' if trigger < 0 else 'after'} event"
                        ttk.Label(alarm_f, text=f"{alarm_type}: {trigger_txt}", style="SmallText.TLabel")\
                            .pack(anchor="w", padx=5)

                attachments = cal_analyser.get_attachments_for_event(event_id)
                if attachments:
                    att_f = ttk.LabelFrame(forensic_content, text="Attachments")
                    att_f.pack(fill="x", pady=3)
                    for att in attachments:
                        filename = att.get('filename', 'file')
                        mime = att.get('mime_type', '')
                        size = att.get('file_size', 0)
                        size_str = ""
                        if size:
                            if size < 1024:
                                size_str = f"{size} B"
                            elif size < 1024 * 1024:
                                size_str = f"{size / 1024:.1f} KB"
                            else:
                                size_str = f"{size / (1024 * 1024):.1f} MB"
                        txt = filename
                        if mime:
                            txt += f" ({mime})"
                        if size_str:
                            txt += f" - {size_str}"
                        ttk.Label(att_f, text=txt, style="SmallText.TLabel").pack(anchor="w", padx=5)

            if i < len(sorted_events) - 1:
                ttk.Separator(content_frame, orient="horizontal").pack(fill="x", pady=8)

    def go_to_today():
        today = datetime.now()
        state.current_year = today.year
        state.current_month = today.month
        update_month_label()
        refresh_calendar()

    def change_month(delta):
        new_month = state.current_month + delta
        new_year = state.current_year
        if new_month < 1:
            new_month = 12
            new_year -= 1
        elif new_month > 12:
            new_month = 1
            new_year += 1
        state.current_year = new_year
        state.current_month = new_month
        update_month_label()
        refresh_calendar()

    refresh_calendar()

    status_frame = ttk.Frame(parent_frame)
    status_frame.pack(fill="x", pady=5)
    event_count = len(state.events_cache.get(f"{state.current_year}-{state.current_month}", pd.DataFrame()))
    ttk.Label(status_frame, text=f"Total events: {event_count}", style="SmallText.TLabel")\
        .pack(side="left")
    ttk.Label(status_frame, text=f"Backup path: {backup_path}", style="SmallText.TLabel")\
        .pack(side="right")
