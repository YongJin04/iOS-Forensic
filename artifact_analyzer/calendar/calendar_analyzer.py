import os
import sqlite3
from datetime import datetime
import pandas as pd


class BackupPathHelper:
    """
    Helper class that locates a file inside an iOS backup using Manifest.db.
    """

    def __init__(self, backup_path: str):
        self.backup_path = backup_path

    def get_file_path_from_manifest(self, relative_path: str) -> str:
        """Return the absolute path to a file referenced in Manifest.db or ``None`` if it
        cannot be resolved."""
        manifest_path = os.path.join(self.backup_path, "Manifest.db")
        if not os.path.exists(manifest_path):
            print(f"[Error] Manifest.db not found: {manifest_path}")
            return None

        try:
            with sqlite3.connect(manifest_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT fileID FROM Files WHERE relativePath = ?", (relative_path,)
                )
                result = cursor.fetchone()

            if result:
                file_hash = result[0]
                file_path = os.path.join(self.backup_path, file_hash[:2], file_hash)
                if os.path.exists(file_path):
                    return file_path
                print(
                    f"[Warning] Hash listed in Manifest.db but file is missing on disk: {file_path}"
                )
            else:
                print(f"[Warning] {relative_path} not found in Manifest.db")
        except Exception as e:
            print(f"[Error] Failed to query Manifest.db: {e}")
        return None


class CalendarAnalyser:
    """
    Analyse the iOS Calendar database extracted from a backup and expose helper
    methods for forensic processing.
    """

    IOS_EPOCH = 978307200  # Seconds between 1970‑01‑01 and 2001‑01‑01

    def __init__(self, backup_path: str):
        self.backup_path = backup_path
        self.default_calendar_db_path = os.path.join(
            backup_path, "Library", "Calendar", "Calendar.sqlitedb"
        )
        self.conn: sqlite3.Connection | None = None
        self.path_helper = BackupPathHelper(backup_path)

    # ---------------------------------------------------------------------
    # Connection helpers
    # ---------------------------------------------------------------------
    def connect_to_db(self) -> bool:
        """Open a read‑only connection to ``Calendar.sqlitedb``.

        Returns ``True`` on success, otherwise ``False``.
        """
        relative_path = "Library/Calendar/Calendar.sqlitedb"
        calendar_db_path = self.path_helper.get_file_path_from_manifest(relative_path)
        if not calendar_db_path:
            print("[Info] Manifest lookup failed. Falling back to default path.")
            calendar_db_path = self.default_calendar_db_path

        if not os.path.exists(calendar_db_path):
            print("[Error] Calendar database file not found.")
            return False

        try:
            # Open read‑only to avoid accidental mutations
            self.conn = sqlite3.connect(f"file:{calendar_db_path}?mode=ro", uri=True)
            self.conn.row_factory = sqlite3.Row
            # print(f"[Success] Connected to calendar DB: {calendar_db_path}")
            return True
        except sqlite3.Error as e:
            print(f"[Error] Could not connect to database: {e}")
            return False

    def close_connection(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _convert_date(self, raw_value) -> datetime | None:
        """Convert CoreData timestamp to ``datetime`` (local time)."""
        try:
            raw_value = float(raw_value)
        except (ValueError, TypeError):
            return None

        # Handle nsdate stored as nanoseconds / milliseconds / seconds since 2001‑01‑01.
        if raw_value > 1e12:
            seconds = raw_value / 1e9
        elif raw_value > 1e9:
            seconds = raw_value / 1e3
        else:
            seconds = raw_value

        try:
            return datetime.fromtimestamp(seconds + self.IOS_EPOCH)
        except Exception:
            return None

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def get_events_for_month(self, year: int, month: int) -> pd.DataFrame:
        """Return a ``DataFrame`` with all events that **start** in ``year``/``month``."""
        if not self.conn and not self.connect_to_db():
            return pd.DataFrame()

        try:
            from calendar import monthrange

            start_date = datetime(year, month, 1)
            end_date = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
            start_ts = start_date.timestamp() - self.IOS_EPOCH
            end_ts = end_date.timestamp() - self.IOS_EPOCH

            query = """
            SELECT ci.ROWID                AS event_id,
                   ci.summary,
                   ci.start_date,
                   ci.end_date,
                   ci.all_day,
                   ci.location_id,
                   ci.description,
                   c.title                AS calendar_title,
                   c.color,
                   c.symbolic_color_name
            FROM   CalendarItem ci
                   LEFT JOIN Calendar c ON ci.calendar_id = c.ROWID
            WHERE  ci.start_date BETWEEN ? AND ?
            ORDER  BY ci.start_date;
            """
            df = pd.read_sql_query(query, self.conn, params=(start_ts, end_ts))
            df["start_date"] = df["start_date"].apply(self._convert_date)
            df["end_date"] = df["end_date"].apply(self._convert_date)
            return df
        except Exception as e:
            print(f"[Error] Failed to query events: {e}")
            return pd.DataFrame()

    def get_event_details(self, event_id: int) -> dict | None:
        if not self.conn and not self.connect_to_db():
            return None
        try:
            query = """
            SELECT ci.*,
                   c.title                AS calendar_title,
                   c.color,
                   c.symbolic_color_name
            FROM   CalendarItem ci
                   LEFT JOIN Calendar c ON ci.calendar_id = c.ROWID
            WHERE  ci.ROWID = ?;
            """
            row = self.conn.execute(query, (event_id,)).fetchone()
            if not row:
                return None

            event = dict(row)
            event["start_date"] = self._convert_date(event["start_date"])
            event["end_date"] = self._convert_date(event["end_date"])
            return event
        except sqlite3.Error as e:
            print(f"[Error] Failed to fetch event details: {e}")
            return None

    # ------------------------------------------------------------------
    # Stub helpers – keep prints in English so that all *visible* output
    # remains English‑only, as requested.
    # ------------------------------------------------------------------
    def get_error_logs(self, event_id: int) -> list:
        print("[Info] The schema contains no ErrorLog table – returning empty list.")
        return []

    def get_event_actions(self, event_id: int) -> list:
        try:
            df = pd.read_sql_query(
                "SELECT * FROM EventAction WHERE event_id = ?", self.conn, params=(event_id,)
            )
            return df.to_dict("records")
        except Exception as e:
            print(f"[Error] Failed to fetch EventAction: {e}")
            return []

    def get_exception_dates(self, event_id: int) -> list:
        try:
            df = pd.read_sql_query(
                "SELECT * FROM ExceptionDate WHERE owner_id = ?", self.conn, params=(event_id,)
            )
            if not df.empty and "date" in df.columns:
                df["date"] = df["date"].apply(
                    lambda x: datetime.strptime(x, "%Y-%m-%d") if isinstance(x, str) else x
                )
            return df.to_dict("records")
        except Exception as e:
            print(f"[Error] Failed to fetch ExceptionDate: {e}")
            return []

    def get_recurrence_info(self, event_id: int) -> list:
        try:
            df = pd.read_sql_query(
                "SELECT * FROM Recurrence WHERE owner_id = ?", self.conn, params=(event_id,)
            )
            return df.to_dict("records")
        except Exception as e:
            print(f"[Error] Failed to fetch RecurrenceInfo: {e}")
            return []

    def get_participants(self, event_id: int) -> list:
        try:
            df = pd.read_sql_query(
                "SELECT * FROM Participant WHERE owner_id = ?", self.conn, params=(event_id,)
            )
            return df.to_dict("records")
        except Exception as e:
            print(f"[Error] Failed to fetch Participant: {e}")
            return []

    def get_location_info(self, location_id: int) -> list:
        try:
            df = pd.read_sql_query(
                "SELECT * FROM Location WHERE ROWID = ?", self.conn, params=(location_id,)
            )
            return df.to_dict("records")
        except Exception as e:
            print(f"[Error] Failed to fetch Location: {e}")
            return []

    def get_alarms_for_event(self, event_id: int) -> list:
        if not self.conn and not self.connect_to_db():
            return []
        try:
            query = """
            SELECT a.ROWID AS alarm_id,
                   a.trigger_date,
                   a.trigger_interval,
                   a.type,
                   a.disabled,
                   ac.occurrence_date,
                   ac.fire_date
            FROM   Alarm a
                   LEFT JOIN AlarmCache ac ON a.ROWID = ac.alarm_id
            WHERE  ac.event_id = ?
            ORDER  BY a.trigger_date;
            """
            df = pd.read_sql_query(query, self.conn, params=(event_id,))
            if not df.empty:
                df["trigger_date"] = df["trigger_date"].apply(self._convert_date)
                df["occurrence_date"] = df["occurrence_date"].apply(self._convert_date)
                df["fire_date"] = df["fire_date"].apply(self._convert_date)
            return df.to_dict("records")
        except Exception as e:
            print(f"[Error] Failed to fetch Alarms: {e}")
            return []

    def get_attachments_for_event(self, event_id: int) -> list:
        if not self.conn and not self.connect_to_db():
            return []
        try:
            df = pd.read_sql_query(
                """
                SELECT ROWID AS attachment_id,
                       owner_id,
                       external_rep,
                       file_id,
                       filename,
                       mime_type,
                       file_size
                FROM   Attachment
                WHERE  owner_id = ?
                ORDER  BY attachment_id;
                """,
                self.conn,
                params=(event_id,),
            )
            return df.to_dict("records")
        except Exception as e:
            print(f"[Error] Failed to fetch Attachments: {e}")
            return []
