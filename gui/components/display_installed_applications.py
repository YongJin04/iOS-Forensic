import os
import plistlib
from tkinter import ttk, messagebox

def parse_itunes_metadata(plist_path, bundle_id):
    try:
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f)
            application = plist.get("Applications")

            # 이미 dict이면 그냥 사용
            if not application or not isinstance(application, dict):
                return "Unknown", ""

            app_info = application.get(bundle_id)
            if not app_info:
                return "Unknown", ""

            iTunesMetadata = app_info.get("iTunesMetadata")
            if not iTunesMetadata or not isinstance(iTunesMetadata, bytes):
                return "Unknown", ""

            iTunesMetadata_plist = plistlib.loads(iTunesMetadata)
            name = iTunesMetadata_plist.get("itemName", "Unknown")
            version = iTunesMetadata_plist.get("bundleShortVersionString", "Unknown")
            return name, version

    except Exception as e:
        print(f"Error parsing iTunesMetadata in {plist_path}: {e}")
        return "Unknown", ""

def display_installed_applications(content_frame, backup_path):
    for widget in content_frame.winfo_children():
        widget.destroy()

    frame = ttk.Frame(content_frame, padding=20)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(frame, text="🛠️ Installed Applications", style="Header.TLabel").pack(anchor="w", pady=(0, 10))

    app_infos = []
    found_installed_list = False

    for root, dirs, files in os.walk(backup_path):
        for file in files:
            if file == "Info.plist":
                plist_path = os.path.join(root, file)
                try:
                    with open(plist_path, 'rb') as f:
                        plist = plistlib.load(f)
                    if "Installed Applications" in plist:
                        installed = plist.get("Installed Applications", [])
                        for bundle_id in installed:
                            # iTunesMetadata 확인
                            # print(bundle_id)
                            name, version = parse_itunes_metadata(plist_path, bundle_id)
                            app_infos.append((bundle_id, name, version))
                        found_installed_list = True
                        break
                except Exception as e:
                    print(f"Error reading Installed Applications from {plist_path}: {e}")

    if not found_installed_list:
        for root, dirs, files in os.walk(backup_path):
            for file in files:
                if file == "Info.plist":
                    plist_path = os.path.join(root, file)
                    try:
                        with open(plist_path, 'rb') as f:
                            plist = plistlib.load(f)
                        bundle_id = plist.get("CFBundleIdentifier", "")
                        name = plist.get("CFBundleDisplayName") or plist.get("CFBundleName", "Unknown")
                        version = plist.get("CFBundleShortVersionString") or plist.get("CFBundleVersion", "")
                        if not name or name == "Unknown":
                            # iTunesMetadata에서 보완
                            m_name, m_version = parse_itunes_metadata(plist_path)
                            name = m_name if name == "Unknown" else name
                            version = m_version if not version else version
                        if bundle_id:
                            app_infos.append((bundle_id, name, version))
                    except Exception as e:
                        print(f"Error reading app Info.plist from {plist_path}: {e}")

    if not app_infos:
        ttk.Label(frame, text="앱 정보를 찾을 수 없습니다.", style="CardText.TLabel").pack(anchor="w")
        return

    tree = ttk.Treeview(frame, columns=("Bundle ID", "Name", "Version"), show="headings", height=25)
    tree.heading("Bundle ID", text="Application ID")
    tree.heading("Name", text="Application Name")
    tree.heading("Version", text="Version")
    tree.column("Bundle ID", width=280, anchor="w")
    tree.column("Name", width=200, anchor="w")
    tree.column("Version", width=100, anchor="center")
    tree.pack(fill="both", expand=True)

    tree.tag_configure("row_0", background="#FFFFFF")
    tree.tag_configure("row_1", background="#F9F9F9")

    for i, (bundle_id, name, version) in enumerate(sorted(app_infos)):
        tree.insert("", "end", values=(bundle_id, name, version), tags=(f"row_{i % 2}",))
