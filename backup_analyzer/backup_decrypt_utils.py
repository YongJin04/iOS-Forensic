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

_SQLITE_MAGIC_HEX = "53514c69746520666f726d6174203300"

def is_backup_encrypted(backup_path: str) -> bool:
    path = os.path.join(backup_path, "Manifest.db")
    try:
        with open(path, "rb") as fp:
            return fp.read(16).hex() != _SQLITE_MAGIC_HEX
    except FileNotFoundError:
        return True

def _center_window(win: tk.Toplevel | tk.Tk, parent: tk.Toplevel | tk.Tk | None = None):
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
    win = tk.Toplevel(parent) if parent else tk.Tk()
    win.title(title)
    tk.Label(win, text=msg, padx=34, pady=22, justify="center").pack()
    tk.Button(win, text="OK", command=win.destroy, width=10).pack(pady=(0, 18))
    _center_window(win, parent)
    win.grab_set()
    win.focus_force()
    win.wait_window()

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

def decrypt_iphone_backup(
    passphrase: str,
    backup_path: str,
    parent: tk.Toplevel | tk.Tk | None = None,
) -> bool:
    """
    • 복호화 작업이 시작되면 `<backup>/.decrypting` 플래그를 만들고,
      이전에 남아 있을 수 있는 `.decryption_complete` 플래그를 제거한다.
    • 작업이 정상적으로 끝나면 `.decrypting` 을 지우고
      `.decryption_complete` 를 새로 만든다.
    • 사용자가 X 버튼을 눌러 프로그레스 창을 닫으면 `cancel_event`
      플래그를 세워 워커 스레드를 중단시키고,
      `.decrypting` 파일을 남겨 Load 를 차단한다.
    """
    if not passphrase:
        _popup("🔑 Please enter the backup password.", "Missing Password", parent)
        return False

    # ── 플래그 파일 준비 ──────────────────────────────────────
    decrypting_flag      = os.path.join(backup_path, ".decrypting")
    completed_flag       = os.path.join(backup_path, ".decryption_complete")
    _safe_remove(completed_flag)                 # 이전 기록 제거
    with open(decrypting_flag, "w") as fp:       # 진행 중 표시
        fp.write(time.strftime("%Y-%m-%d %H:%M:%S"))

    # ── GUI 생성(원본 코드와 동일 + cancel 이벤트 추가) ──────
    gui_root = parent or tk._get_default_root()  # type: ignore[attr-defined]
    created_root = False
    if gui_root is None:
        gui_root = tk.Tk()
        gui_root.withdraw()
        created_root = True

    prog = tk.Toplevel(gui_root)
    prog.title("Decrypting iPhone Backup")
    tk.Label(prog, text="Decrypting backup...", pady=12).pack()
    bar = ttk.Progressbar(prog, length=560, mode="determinate")
    bar.pack(padx=18, pady=6)

    info_fr = tk.Frame(prog)
    info_fr.pack(pady=(0, 14))

    # ── 시간·카운터 라벨(원본과 동일) ────────────────────────
    tk.Label(info_fr, text="Elapsed time:").grid(row=0, column=0, sticky="w")
    elapsed_val = tk.Label(info_fr, relief="sunken", width=10, anchor="e", text="0:00:00")
    elapsed_val.grid(row=0, column=1, sticky="w", padx=(4, 0))

    tk.Label(info_fr, text="Estimated time left:").grid(row=1, column=0, sticky="w", pady=(4, 0))
    eta_val = tk.Label(info_fr, relief="sunken", width=10, anchor="e", text="--:--:--")
    eta_val.grid(row=1, column=1, sticky="w", padx=(4, 0), pady=(4, 0))

    counter_lbl = tk.Label(info_fr, text="0/0 files", anchor="center", justify="center")
    counter_lbl.grid(row=2, column=0, columnspan=2, pady=(6, 0))

    _center_window(prog, gui_root)

    # ── 작업·취소 핸들러 설정 ─────────────────────────────────
    q: queue.Queue = queue.Queue()
    cancel_event = threading.Event()
    result_success = False

    def on_cancel():
        """X 버튼(또는 Alt+F4) → 복호화 중단 플래그."""
        cancel_event.set()
        prog.destroy()            # UI 즉시 닫기

    prog.protocol("WM_DELETE_WINDOW", on_cancel)

    # ── 워커 스레드 ───────────────────────────────────────────
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
                    q.put(("error", "Incorrect password. Please try again."))
                    return
            _atomic_replace(manifest_tmp, manifest_dst)
        except Exception as e:
            _safe_remove(manifest_tmp)
            q.put(("error", f"Error decrypting Manifest.db\n{e}"))
            return

        # ── 파일 목록 취득 ───────────────────────────────────
        try:
            conn = sqlite3.connect(manifest_dst)
            cur = conn.cursor()
            cur.execute("SELECT fileID, relativePath FROM Files WHERE Flags != 2")
            files = cur.fetchall()
            conn.close()
        except Exception as e:
            q.put(("error", f"Error reading Manifest.db\n{e}"))
            return

        q.put(("total", len(files), start_time))
        success_cnt = fail_cnt = 0

        for idx, (fid, rel) in enumerate(files, 1):
            # 취소 감지
            if cancel_event.is_set():
                q.put(("cancelled",))
                return

            if not rel:
                q.put(("progress", idx, success_cnt, fail_cnt, start_time))
                continue

            enc = os.path.join(backup_path, fid[:2], fid)
            tmp = enc + "_temp"
            if not os.path.exists(enc):
                fail_cnt += 1
                q.put(("progress", idx, success_cnt, fail_cnt, start_time))
                continue

            try:
                backup.extract_file(relative_path=rel, output_filename=tmp)
                os.remove(enc)
                os.rename(tmp, enc)
                success_cnt += 1
            except Exception:
                # 복구 실패 시에도 취소 플래그 우선 확인
                if cancel_event.is_set():
                    q.put(("cancelled",))
                    return
                fail_cnt += 1
            finally:
                q.put(("progress", idx, success_cnt, fail_cnt, start_time))

        q.put(("done", success_cnt, fail_cnt))

    threading.Thread(target=worker, daemon=True).start()

    # ── GUI 폴링 루프 ────────────────────────────────────────
    total_files = 0
    start_time_ref = None

    def _sec_to_hms(sec: float) -> str:
        if sec <= 0 or sec == float("inf"):
            return "--:--:--"
        m, s = divmod(int(sec + 0.5), 60)
        h, m = divmod(m, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

    def _poll():
        nonlocal total_files, start_time_ref, result_success
        while not q.empty():
            tag, *payload = q.get()
            if tag == "error":
                prog.destroy()
                _popup(payload[0], "Error", gui_root)
                return
            if tag == "cancelled":
                _popup("Decryption cancelled by user.\n"
                       "Load will be disabled until you restart decryption.",
                       "Cancelled", gui_root)
                return                                   # .decrypting 그대로 둠
            if tag == "total":
                total_files, start_time_ref = payload
                bar.config(maximum=total_files)
                counter_lbl.config(text=f"0/{total_files} files")
            elif tag == "progress":
                current, succ, fail, st = payload
                bar["value"] = current
                counter_lbl.config(text=f"{current}/{total_files} files")
                elapsed = time.time() - st
                remaining = (elapsed / current * (total_files - current)) if current else float("inf")
                elapsed_val.config(text=_sec_to_hms(elapsed))
                eta_val.config(text=_sec_to_hms(remaining))
        prog.after(100, _poll)

    _poll()
    if created_root:
        gui_root.mainloop()
    else:
        gui_root.wait_window(prog)

    # 성공 여부 반환
    return result_success
