import unicodedata, re, sys, shutil, time, io, threading
from pathlib import Path
from getpass import getpass
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

import requests
from pyicloud import PyiCloudService
from pyicloud.exceptions import (
    PyiCloudFailedLoginException,
    PyiCloudAPIResponseException,
)

from tqdm import tqdm

# ────────────────────────────────────────────────────────────
# 1. Apple ID Authentication
# ────────────────────────────────────────────────────────────
def _login(email: str | None = None, password: str | None = None) -> PyiCloudService:
    if email is None:
        email = input("Apple ID (email): ").strip()
    if password is None:
        password = getpass("Password: ").strip()
    return PyiCloudService(email, password)

def authenticate(email: str | None = None,
                 password: str | None = None,
                 code_cb=None) -> PyiCloudService:
    try:
        api = _login(email, password)
    except PyiCloudFailedLoginException:
        cookie_dir = Path.home() / ".pyicloud"
        if cookie_dir.exists():
            shutil.rmtree(cookie_dir, ignore_errors=True)
            print("⚠️  Corrupted session cookies deleted. Retrying login.")
        api = _login(email, password)

    if api.requires_2fa:
        code = code_cb() if code_cb else input("Enter the 6-digit 2FA code shown on your trusted device: ").strip()
        if not api.validate_2fa_code(code):
            sys.exit("❌ 2FA authentication failed – exiting")
        api.trust_session()
    if not api.is_trusted_session:
        sys.exit("❌ Failed to trust session – exiting")
    return api


# ────────────────────────────────────────────────────────────
# 2. File/Folder Name Sanitization
# ────────────────────────────────────────────────────────────
_WINDOWS_FORBIDDEN = re.compile(r'[<>:"/\\|?*]')

def sanitize(name: str) -> str:
    name = unicodedata.normalize("NFC", name)
    name = _WINDOWS_FORBIDDEN.sub("_", name)
    name = name.rstrip(" .")
    return name or "untitled"


# ────────────────────────────────────────────────────────────
# 3. Single File Download + 503 Error Handling
# ────────────────────────────────────────────────────────────
_MAX_RETRY = 5
_RETRY_BACKOFF = 3

def download_file(cloud_file,
                  local_path: Path,
                  log_func=None,
                  throttle: float = .5) -> None:

    local_path.parent.mkdir(parents=True, exist_ok=True)
    total = getattr(cloud_file, "size", None)
    if total and local_path.exists() and local_path.stat().st_size == total:
        log_func and log_func(f"{local_path.name}: Already exists ({total//1024}k)")
        return

    bar = tqdm(total=total, unit="B", unit_scale=True,
               desc=local_path.name, mininterval=0, file=io.StringIO())

    def _progress_print():
        rate_kb = (bar.format_dict['rate'] or 0) / 1024
        done_k  = bar.n // 1024
        total_k = (bar.total // 1024) if bar.total else '?'
        log_func and log_func(f"{local_path.name}: {done_k}k/{total_k}k  ({rate_kb:4.0f} kB/s)")

    attempt = 0
    while attempt < _MAX_RETRY:
        try:
            with cloud_file.open(stream=True) as resp:
                start_t = last_t = time.time()
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))

                            if time.time() - last_t >= throttle or bar.n == bar.total:
                                _progress_print()
                                last_t = time.time()

            bar.close()
            _progress_print()
            return
        except (PyiCloudAPIResponseException, requests.exceptions.RequestException) as e:
            if (
                "503" not in str(e)
                and getattr(e, "code", None) != 503
                and getattr(e, "status_code", None) != 503
            ):
                raise

            attempt += 1
            if attempt >= _MAX_RETRY:
                raise

            delay = _RETRY_BACKOFF * (2 ** (attempt - 1))
            log_func and log_func(f"⚠️  503 error – retrying in {delay}s "
                                  f"({attempt}/{_MAX_RETRY})")
            time.sleep(delay)
            bar.reset()
            if local_path.exists():
                try:
                    local_path.unlink()
                except Exception:
                    pass


# ────────────────────────────────────────────────────────────
# 4. Recursive Folder/Root Traversal
# ────────────────────────────────────────────────────────────
def recurse_download(node, target_dir: Path, log_func=None):
    ntype = getattr(node, "type", "root")
    if ntype == "file":
        download_file(node, target_dir / sanitize(node.name), log_func=log_func)
        return

    current = target_dir if ntype == "root" else target_dir / sanitize(node.name)
    for child in node.get_children():
        recurse_download(child, current, log_func=log_func)


# ────────────────────────────────────────────────────────────
# 5-A. GUI Mode
# ────────────────────────────────────────────────────────────
def gui_download(parent: tk.Misc | None = None,
                 dest_root: Path | None = None,
                 on_complete=None) -> None:
    dest_root = dest_root or (Path.cwd() / "iCloud_Drive_Backup")

    win = tk.Toplevel(parent)
    win.title("iCloud Account Login")
    win.minsize(450, 280)
    win.resizable(True, True)

    frm = ttk.Frame(win, padding=16)
    frm.grid(row=0, column=0, sticky="nsew")
    win.rowconfigure(0, weight=1)
    win.columnconfigure(0, weight=1)

    ttk.Label(frm, text="Apple ID").grid(row=0, column=0, sticky="e")
    ttk.Label(frm, text="Password").grid(row=1, column=0, sticky="e", pady=(6, 0))

    entry_id = ttk.Entry(frm)
    entry_pw = ttk.Entry(frm, show="•")
    entry_id.grid(row=0, column=1, sticky="ew", padx=(6, 0))
    entry_pw.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))
    frm.columnconfigure(1, weight=1)

    log_box = tk.Text(frm, height=10, wrap="none", state="disabled")
    log_box.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="nsew")
    frm.rowconfigure(2, weight=1)

    progress = ttk.Progressbar(frm, mode="indeterminate")
    progress.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def safe_log(msg: str):
        def _append():
            log_box.configure(state="normal")
            log_box.insert("end", f"{msg}\n")
            log_box.see("end")
            log_box.configure(state="disabled")
        win.after(0, _append)

    def start_download():
        email = entry_id.get().strip()
        pw = entry_pw.get().strip()
        if not email or not pw:
            messagebox.showwarning("Input Error", "Please enter both Apple ID and password.", parent=win)
            return

        btn_start.config(state="disabled")
        progress.start(10)
        safe_log("🔐 Authenticating with iCloud…")

        def worker():
            try:
                code_prompt = lambda: simpledialog.askstring(
                    "2-Factor Authentication",
                    "Enter the 6-digit code shown on your trusted device",
                    parent=win,
                ) or ""

                api = authenticate(email, pw, code_prompt)
                safe_log("✅ Login successful – starting backup")
                recurse_download(api.drive, dest_root, log_func=safe_log)
                safe_log("🎉 All files downloaded successfully!")
                messagebox.showinfo("Download Complete", "iCloud backup is complete.", parent=win)
            except Exception as e:
                safe_log(f"❌ Error: {e}")
                messagebox.showerror("Error", str(e), parent=win)
            finally:
                progress.stop()
                btn_start.config(state="normal")
                if on_complete:
                    win.after(0, on_complete)

        threading.Thread(target=worker, daemon=True).start()

    btn_start = ttk.Button(frm, text="Start Sync", command=start_download, width=18)
    btn_start.grid(row=4, column=0, columnspan=2, pady=(12, 0))

    win.grab_set()
    win.transient(parent)


# ────────────────────────────────────────────────────────────
# 5-B. CLI Mode
# ────────────────────────────────────────────────────────────
def main() -> None:
    api = authenticate()
    dest_root = Path.cwd() / "iCloud_Drive_Backup"
    print(f"📂 Starting backup to: {dest_root}")
    recurse_download(api.drive, dest_root, log_func=print)

if __name__ == "__main__":
    main()
