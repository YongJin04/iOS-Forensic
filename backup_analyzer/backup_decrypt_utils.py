import os
import stat
import sqlite3
import shutil
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
from uuid import uuid4
from iphone_backup_decrypt import EncryptedBackup

# SQLite magic bytes ("SQLite format 3\0")
_SQLITE_MAGIC_HEX = "53514c69746520666f726d6174203300"

def is_backup_encrypted(backup_path: str) -> bool:
    """Return *True* if Manifest.db header is **not** plain SQLite."""
    path = os.path.join(backup_path, "Manifest.db")
    try:
        with open(path, "rb") as fp:
            return fp.read(16).hex() != _SQLITE_MAGIC_HEX
    except FileNotFoundError:
        return True

def _center_window(win: tk.Toplevel | tk.Tk, parent: tk.Toplevel | tk.Tk | None = None):
    """Center *win* over *parent* (or screen)."""
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    if parent and parent.winfo_exists():
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    else:
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x, y = (sw - w) // 2, (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


def _popup(msg: str, title: str = "Notice", parent: tk.Toplevel | tk.Tk | None = None):
    """Modal message popup."""
    win = tk.Toplevel(parent) if parent else tk.Tk()
    win.title(title)
    tk.Label(win, text=msg, padx=34, pady=22, justify="center").pack()
    tk.Button(win, text="OK", command=win.destroy, width=10).pack(pady=(0, 18))
    _center_window(win, parent)
    win.grab_set(); win.focus_force(); win.wait_window()

# ─────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────

def _safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)
    except PermissionError:
        pass


def _atomic_replace(src: str, dst: str):
    try:
        os.replace(src, dst)
        return
    except PermissionError:
        if os.path.exists(dst):
            os.chmod(dst, stat.S_IWRITE)
            try:
                os.replace(src, dst)
                return
            except PermissionError:
                pass
    try:
        shutil.copyfile(src, dst)
        os.chmod(dst, stat.S_IWRITE)
        _safe_remove(src)
    except Exception as exc:
        raise PermissionError(f"Failed to overwrite '{dst}' → {exc}") from exc

# ─────────────────────────────────────────────────────────────
# Main entry
# ─────────────────────────────────────────────────────────────

def decrypt_iphone_backup(passphrase: str, backup_path: str, parent: tk.Toplevel | tk.Tk | None = None) -> bool:
    """Decrypt an encrypted iPhone backup and show a rich progress window."""

    if not passphrase:
        _popup("🔑 Please enter the backup password.", "Missing Password", parent)
        return False

    # root context
    gui_root = parent or tk._get_default_root()  # type: ignore[attr-defined]
    created_root = False
    if gui_root is None:
        gui_root = tk.Tk(); gui_root.withdraw(); created_root = True

    # ── progress window ──
    prog = tk.Toplevel(gui_root)
    prog.title("Decrypting iPhone Backup")
    tk.Label(prog, text="📂 Decrypting backup...", pady=12).pack()
    bar = ttk.Progressbar(prog, length=560, mode="determinate")
    bar.pack(padx=18, pady=6)
    pct_lbl = tk.Label(prog, text="0%")
    pct_lbl.pack(pady=(0, 6))

    # detailed info frame (elapsed / ETA) like screenshot
    info_fr = tk.Frame(prog)
    info_fr.pack(pady=(0, 14))

    tk.Label(info_fr, text="Elapsed time:").grid(row=0, column=0, sticky="w")
    elapsed_val = tk.Label(info_fr, relief="sunken", width=10, anchor="e", text="0:00:00")
    elapsed_val.grid(row=0, column=1, sticky="w", padx=(4, 0))

    tk.Label(info_fr, text="Estimated time left:").grid(row=1, column=0, sticky="w", pady=(4, 0))
    eta_val = tk.Label(info_fr, relief="sunken", width=10, anchor="e", text="--:--:--")
    eta_val.grid(row=1, column=1, sticky="w", padx=(4, 0), pady=(4, 0))

    counter_lbl = tk.Label(info_fr, text="0/0 files")
    counter_lbl.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

    _center_window(prog, gui_root)

    q: queue.Queue = queue.Queue()
    result_success = False

    # ── worker thread ──
    def worker():
        manifest_tmp = os.path.join(backup_path, f"_manifest_{uuid4().hex}.dec")
        manifest_dst = os.path.join(backup_path, "Manifest.db")
        start_time = time.time()

        try:
            backup = EncryptedBackup(backup_directory=backup_path, passphrase=passphrase)
            backup.save_manifest_file(manifest_tmp)
            with open(manifest_tmp, "rb") as fp:
                if fp.read(16).hex() != _SQLITE_MAGIC_HEX:
                    _safe_remove(manifest_tmp)
                    q.put(("error", "❗ Incorrect password. Please try again."))
                    return
            try:
                _atomic_replace(manifest_tmp, manifest_dst)
            except PermissionError as exc:
                _safe_remove(manifest_tmp)
                q.put(("error", f"Error replacing Manifest.db\n{exc}"))
                return
        except Exception as e:
            _safe_remove(manifest_tmp)
            q.put(("error", f"Error decrypting Manifest.db\n{e}"))
            return

        # list files to decrypt
        try:
            conn = sqlite3.connect(manifest_dst)
            cur = conn.cursor(); cur.execute("SELECT fileID, relativePath FROM Files WHERE Flags != 2")
            files = cur.fetchall(); conn.close()
        except Exception as e:
            q.put(("error", f"Error reading Manifest.db\n{e}")); return

        q.put(("total", len(files), start_time))
        success_cnt = fail_cnt = 0
        for idx, (fid, rel) in enumerate(files, 1):
            if not rel:
                q.put(("progress", idx, success_cnt, fail_cnt, start_time)); continue

            enc = os.path.join(backup_path, fid[:2], fid)
            tmp = enc + "_temp"
            if not os.path.exists(enc):
                fail_cnt += 1
                q.put(("progress", idx, success_cnt, fail_cnt, start_time)); continue

            try:
                backup.extract_file(relative_path=rel, output_filename=tmp)
                os.remove(enc); os.rename(tmp, enc)
                success_cnt += 1
            except Exception as e:
                # treat size‑mismatch warnings as success
                if "decrypted" in str(e) and "expected" in str(e):
                    if os.path.exists(tmp):
                        os.remove(enc); os.rename(tmp, enc)
                    success_cnt += 1
                elif os.path.exists(tmp):
                    try:
                        os.remove(enc); os.rename(tmp, enc)
                        success_cnt += 1
                    except Exception:
                        fail_cnt += 1
                else:
                    fail_cnt += 1
            finally:
                q.put(("progress", idx, success_cnt, fail_cnt, start_time))
        q.put(("done", success_cnt, fail_cnt))

    threading.Thread(target=worker, daemon=True).start()

    total_files = 0; start_time_ref = None

    # formatting helpers
    def _sec_to_hms(sec: float) -> str:
        if sec <= 0 or sec == float('inf'): return "--:--:--"
        m, s = divmod(int(sec + 0.5), 60); h, m = divmod(m, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

    # ── poll queue ──
    def _poll():
        nonlocal total_files, start_time_ref, result_success
        while not q.empty():
            tag, *payload = q.get()
            if tag == "error":
                prog.destroy(); _popup(payload[0], "Error", gui_root); _close_root(); return
            if tag == "total":
                total_files, start_time_ref = payload
                bar.config(maximum=total_files)
                counter_lbl.config(text=f"0/{total_files} files")
            elif tag == "progress":
                current, succ, fail, st = payload
                bar["value"] = current
                pct_lbl.config(text=f"{int(current / (total_files or 1) * 100)}%")
                counter_lbl.config(text=f"{current}/{total_files} files")
                elapsed = time.time() - st
                remaining = (elapsed / current * (total_files - current)) if current else float('inf')
                elapsed_val.config(text=_sec_to_hms(elapsed))
                eta_val.config(text=_sec_to_hms(remaining))
            elif tag == "done":
                s, f = payload; prog.destroy()
                messagebox.showinfo("Decryption Complete", f"📊 Completed: {s} succeeded / {f} failed", parent=gui_root)
                result_success = True; _close_root(); return
        prog.after(100, _poll)

    def _close_root():
        if created_root:
            gui_root.quit()

    _poll()
    if created_root:
        gui_root.mainloop()
    else:
        gui_root.wait_window(prog)
    return result_success