import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
from gui.components.display_device_info import *
from gui.components.display_browser import *
from gui.components.display_message import *
from gui.components.display_kakaotalk import *
from gui.components.display_addressbook import *
from gui.components.display_photos_media import *
from gui.components.display_call_history import *
from gui.components.display_sms import *
from gui.components.display_calendar import *
from gui.components.display_installed_applications import *
from gui.components.display_bluetooth import *
from gui.components.display_user_account import *
from gui.components.display_wifi import *
from backup_analyzer.build_tree import *
from gui.components.display_instagram import *
from gui.components.display_notes import *
from gui.components.display_iCloud import *
from gui.components.display_document import *
from gui.components.display_LinkedIn import *
from gui.components.display_line import *

def load_icon(icon_path, size=(20, 20)):
    """아이콘 이미지를 로드합니다."""
    try:
        if os.path.exists(icon_path):
            image = Image.open(icon_path).resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        else:
            print(f"Icon file not found: {icon_path}")
    except Exception as e:
        print(f"Error loading icon {icon_path}: {e}")
    return None

def show_artifact_welcome_page(content_frame):
    """Display the artifact analysis start page."""
    # Clear existing widgets
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    # Display welcome message and guide
    welcome_frame = ttk.Frame(content_frame, style="Card.TFrame", padding=20)
    welcome_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    ttk.Label(welcome_frame, text="iOS Backup Artifact Analysis", 
              style="CardHeader.TLabel", font=("Arial", 18, "bold")).pack(pady=(0, 20))
    
    ttk.Label(welcome_frame, text="Select an artifact category on the left to begin analysis.",
              style="CardText.TLabel", font=("Arial", 12), wraplength=400).pack(pady=10)
    
    # Icon descriptions with real PNG icons grouped by category
    icon_frame = ttk.Frame(welcome_frame)
    icon_frame.pack(pady=30)
    
    # Communication group (6 items)
    comm_icons = [
        {"icon": "gui/icon/imessage.png", "text": "iMessage"},
        {"icon": "gui/icon/kakaotalk.png", "text": "KakaoTalk"},
        {"icon": "gui/icon/instagram.png", "text": "Instagram"},
        {"icon": "gui/icon/line.png", "text": "Line"},
        {"icon": "gui/icon/linkedin.png", "text": "LinkedIn"},
        {"icon": "gui/icon/browser.png", "text": "Browser"}
    ]
    
    comm_row = ttk.Frame(icon_frame)
    comm_row.pack(pady=10)
    
    for icon_data in comm_icons:
        icon_item = ttk.Frame(comm_row)
        icon_item.pack(side="left", padx=10)
        
        icon_image = load_icon(icon_data["icon"], size=(40, 40))
        if icon_image:
            icon_label = ttk.Label(icon_item, image=icon_image)
            icon_label.image = icon_image
            icon_label.pack(anchor="center", pady=(0, 5))
        
        ttk.Label(icon_item, text=icon_data["text"], 
                  style="CardText.TLabel", font=("Arial", 9)).pack(anchor="center")
    
    # Contacts group (2 items)
    contact_icons = [
        {"icon": "gui/icon/contacts.png", "text": "Contact"},
        {"icon": "gui/icon/call_history.png", "text": "Call History"}
    ]
    
    contact_row = ttk.Frame(icon_frame)
    contact_row.pack(pady=10)
    
    for icon_data in contact_icons:
        icon_item = ttk.Frame(contact_row)
        icon_item.pack(side="left", padx=15)
        
        icon_image = load_icon(icon_data["icon"], size=(40, 40))
        if icon_image:
            icon_label = ttk.Label(icon_item, image=icon_image)
            icon_label.image = icon_image
            icon_label.pack(anchor="center", pady=(0, 5))
        
        ttk.Label(icon_item, text=icon_data["text"], 
                  style="CardText.TLabel", font=("Arial", 9)).pack(anchor="center")
    
    # Media group (2 items)
    media_icons = [
        {"icon": "gui/icon/gallery.png", "text": "Gallery"},
        {"icon": "gui/icon/notes.png", "text": "Notes"}
    ]
    
    media_row = ttk.Frame(icon_frame)
    media_row.pack(pady=10)
    
    for icon_data in media_icons:
        icon_item = ttk.Frame(media_row)
        icon_item.pack(side="left", padx=15)
        
        icon_image = load_icon(icon_data["icon"], size=(40, 40))
        if icon_image:
            icon_label = ttk.Label(icon_item, image=icon_image)
            icon_label.image = icon_image
            icon_label.pack(anchor="center", pady=(0, 5))
        
        ttk.Label(icon_item, text=icon_data["text"], 
                  style="CardText.TLabel", font=("Arial", 9)).pack(anchor="center")
    
    # System group (3 items)
    system_icons = [
        {"icon": "gui/icon/device_info.png", "text": "Device Info"},
        {"icon": "gui/icon/applications.png", "text": "Applications"},
        {"icon": "gui/icon/user_account.png", "text": "User Account"}
    ]
    
    system_row = ttk.Frame(icon_frame)
    system_row.pack(pady=10)
    
    for icon_data in system_icons:
        icon_item = ttk.Frame(system_row)
        icon_item.pack(side="left", padx=15)
        
        icon_image = load_icon(icon_data["icon"], size=(40, 40))
        if icon_image:
            icon_label = ttk.Label(icon_item, image=icon_image)
            icon_label.image = icon_image
            icon_label.pack(anchor="center", pady=(0, 5))
        
        ttk.Label(icon_item, text=icon_data["text"], 
                  style="CardText.TLabel", font=("Arial", 9)).pack(anchor="center")
    
    # Network group (2 items)
    network_icons = [
        {"icon": "gui/icon/wifi.png", "text": "Wi-Fi"},
        {"icon": "gui/icon/bluetooth.png", "text": "Bluetooth"}
    ]
    
    network_row = ttk.Frame(icon_frame)
    network_row.pack(pady=10)
    
    for icon_data in network_icons:
        icon_item = ttk.Frame(network_row)
        icon_item.pack(side="left", padx=15)
        
        icon_image = load_icon(icon_data["icon"], size=(40, 40))
        if icon_image:
            icon_label = ttk.Label(icon_item, image=icon_image)
            icon_label.image = icon_image
            icon_label.pack(anchor="center", pady=(0, 5))
        
        ttk.Label(icon_item, text=icon_data["text"], 
                  style="CardText.TLabel", font=("Arial", 9)).pack(anchor="center")
    
    # Cloud & Storage group (3 items)
    cloud_icons = [
        {"icon": "gui/icon/icloud.png", "text": "iCloud"},
        {"icon": "gui/icon/document.png", "text": "Document"},
        {"icon": "gui/icon/calendar.png", "text": "Calendar"}
    ]
    
    cloud_row = ttk.Frame(icon_frame)
    cloud_row.pack(pady=10)
    
    for icon_data in cloud_icons:
        icon_item = ttk.Frame(cloud_row)
        icon_item.pack(side="left", padx=15)
        
        icon_image = load_icon(icon_data["icon"], size=(40, 40))
        if icon_image:
            icon_label = ttk.Label(icon_item, image=icon_image)
            icon_label.image = icon_image
            icon_label.pack(anchor="center", pady=(0, 5))
        
        ttk.Label(icon_item, text=icon_data["text"], 
                  style="CardText.TLabel", font=("Arial", 9)).pack(anchor="center")

def create_artifact_analysis_options(parent, backup_path_var, colors):
    """Create artifact analysis options with improved sidebar layout."""
    main_frame = ttk.Frame(parent)
    main_frame.pack(fill="both", expand=True)

    sidebar = ttk.Frame(main_frame, style="Sidebar.TFrame", padding=10, width=320)
    sidebar.pack(side="left", fill="y", padx=(0, 10))
    sidebar.pack_propagate(False)

    content_frame = ttk.Frame(main_frame, style="Content.TFrame", padding=10)
    content_frame.pack(side="right", fill="both", expand=True)

    header_frame = ttk.Frame(sidebar, style="SidebarHeader.TFrame")
    header_frame.pack(fill="x", pady=(0, 10))
    
    ttk.Label(header_frame, text="Artifact Categories", 
              style="SidebarHeaderTitle.TLabel", font=("Arial", 12, "bold")).pack(anchor="w")

    search_frame = ttk.Frame(sidebar)
    search_frame.pack(fill="x", pady=(0, 10))
    
    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Arial", 9))
    search_entry.pack(fill="x")
    search_entry.insert(0, "🔍 Search...")
    
    def on_search_focus_in(event):
        if search_entry.get() == "🔍 Search...":
            search_entry.delete(0, "end")
    
    def on_search_focus_out(event):
        if search_entry.get() == "":
            search_entry.insert(0, "🔍 Search...")
    
    search_entry.bind("<FocusIn>", on_search_focus_in)
    search_entry.bind("<FocusOut>", on_search_focus_out)

    sidebar_canvas = tk.Canvas(sidebar, highlightthickness=0)
    sidebar_scrollbar = ttk.Scrollbar(sidebar, orient="vertical", command=sidebar_canvas.yview)
    sidebar_scrollable = ttk.Frame(sidebar_canvas)

    sidebar_scrollable.bind(
        "<Configure>",
        lambda e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
    )

    sidebar_canvas.create_window((0, 0), window=sidebar_scrollable, anchor="nw", width=300)
    sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

    sidebar_canvas.pack(side="left", fill="both", expand=True)
    sidebar_scrollbar.pack(side="right", fill="y")

    category_groups = {
        "💬 Communication": [
            {"name": "iMessage", "icon": "gui/icon/imessage.png", "command": lambda: display_imessage(content_frame, backup_path_var.get())},
            {"name": "KakaoTalk", "icon": "gui/icon/kakaotalk.png", "command": lambda: display_kakaotalk(content_frame, backup_path_var.get())},
            {"name": "Instagram", "icon": "gui/icon/instagram.png", "command": lambda: display_instagram(content_frame, backup_path_var.get())},
            {"name": "Line", "icon": "gui/icon/line.png", "command": lambda: display_line(content_frame, backup_path_var.get())},
            {"name": "LinkedIn", "icon": "gui/icon/linkedin.png", "command": lambda: display_LinkedIn(content_frame, backup_path_var.get())},
            {"name": "Browser", "icon": "gui/icon/browser.png", "command": lambda: display_browser(content_frame, backup_path_var.get())},
        ],
        "📞 Contacts": [
            {"name": "Contact", "icon": "gui/icon/contacts.png", "command": lambda: display_contact_content(content_frame, backup_path_var.get())},
            {"name": "Call History", "icon": "gui/icon/call_history.png", "command": lambda: display_call_history(content_frame, backup_path_var.get())},
        ],
        "📁 Media": [
            {"name": "Gallery", "icon": "gui/icon/gallery.png", "command": lambda: display_photos_media(content_frame, backup_path_var.get())},
            {"name": "Notes", "icon": "gui/icon/notes.png", "command": lambda: display_notes(content_frame, backup_path_var.get())},
        ],
        "⚙️ System": [
            {"name": "Device Info", "icon": "gui/icon/device_info.png", "command": lambda: display_device_info(content_frame, backup_path_var.get())},
            {"name": "Applications", "icon": "gui/icon/applications.png", "command": lambda: display_installed_applications(content_frame, backup_path_var.get())},
            {"name": "User Account", "icon": "gui/icon/user_account.png", "command": lambda: display_user_account(content_frame, backup_path_var.get())},
        ],
        "🔒 Network": [
            {"name": "Wi-Fi", "icon": "gui/icon/wifi.png", "command": lambda: display_wifi(content_frame, backup_path_var.get())},
            {"name": "Bluetooth", "icon": "gui/icon/bluetooth.png", "command": lambda: display_bluetooth(content_frame, backup_path_var.get())},
        ],
        "☁️ Cloud & Storage": [
            {"name": "iCloud", "icon": "gui/icon/icloud.png", "command": lambda: display_iCloud(content_frame, backup_path_var.get())},
            {"name": "Document", "icon": "gui/icon/document.png", "command": lambda: display_document(content_frame, backup_path_var.get())},
            {"name": "Calendar", "icon": "gui/icon/calendar.png", "command": lambda: display_calendar(content_frame, backup_path_var.get())},
        ]
    }

    selected_category = tk.StringVar()
    category_buttons_data = []
    group_header_frames = {}

    def create_compact_category_button(category, group_name):
        btn_frame = ttk.Frame(sidebar_scrollable, style="SidebarItem.TFrame", padding=3)
        indicator = ttk.Frame(btn_frame, width=2, style="Indicator.TFrame")
        indicator.pack(side="left", fill="y", padx=(0, 8))

        icon = load_icon(category["icon"], size=(16, 16))
        if icon:
            btn = ttk.Button(btn_frame, text=f" {category['name']}", image=icon, 
                             compound="left", style="CompactSidebar.TButton")
            btn.image = icon
        else:
            btn = ttk.Button(btn_frame, text=category['name'], style="CompactSidebar.TButton")
        
        btn.pack(fill="x", expand=True)

        def on_click():
            activate_category(category, btn_frame, indicator)
        
        btn.configure(command=on_click)
        
        return {
            "button": btn, 
            "indicator": indicator, 
            "frame": btn_frame,
            "category": category,
            "group": group_name
        }

    def activate_category(category, btn_frame, indicator):
        selected_category.set(category["name"])
        for btn_data in category_buttons_data:
            btn_data["frame"].configure(style="SidebarItem.TFrame")
            btn_data["indicator"].configure(style="Indicator.TFrame")
        
        btn_frame.configure(style="SidebarItemActive.TFrame")
        indicator.configure(style="IndicatorActive.TFrame")
        
        if category["command"]:
            category["command"]()

    def filter_categories(search_term):
        search_term = search_term.lower().strip()
        if search_term == "🔍 search...":
            search_term = ""
        
        # 모든 위젯을 먼저 숨기기
        for group_frame in group_header_frames.values():
            group_frame.pack_forget()
        for btn_data in category_buttons_data:
            btn_data["frame"].pack_forget()
        
        # 원래 순서대로 다시 표시
        for group_name, categories in category_groups.items():
            visible_in_group = 0
            
            # 해당 그룹의 카테고리들 체크
            for category in categories:
                category_name = category["name"].lower()
                if search_term == "" or search_term in category_name:
                    visible_in_group += 1
            
            # 그룹에 보여줄 항목이 있으면 그룹 헤더 표시
            if visible_in_group > 0:
                group_header_frames[group_name].pack(fill="x", pady=(8, 2))
                
                # 해당 그룹의 버튼들을 원래 순서대로 표시
                for btn_data in category_buttons_data:
                    if btn_data["group"] == group_name:
                        category_name = btn_data["category"]["name"].lower()
                        if search_term == "" or search_term in category_name:
                            btn_data["frame"].pack(fill="x", pady=1)
        
        sidebar_canvas.update_idletasks()
        sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))

    search_var.trace("w", lambda *args: filter_categories(search_var.get()))

    for group_name, categories in category_groups.items():
        group_frame = ttk.Frame(sidebar_scrollable, padding=(0, 8, 0, 2))
        group_frame.pack(fill="x", pady=(8, 2))
        group_header_frames[group_name] = group_frame
        
        ttk.Label(group_frame, text=group_name, 
                  font=("Arial", 9, "bold"), style="GroupHeader.TLabel").pack(anchor="w")
        
        for category in categories:
            btn_data = create_compact_category_button(category, group_name)
            btn_data["frame"].pack(fill="x", pady=1)
            category_buttons_data.append(btn_data)

    # Mousewheel binding for sidebar area
    def _on_mousewheel(event):
        sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def bind_mousewheel(widget):
        widget.bind("<MouseWheel>", _on_mousewheel)
        widget.bind("<Button-4>", lambda e: sidebar_canvas.yview_scroll(-1, "units"))
        widget.bind("<Button-5>", lambda e: sidebar_canvas.yview_scroll(1, "units"))
        for child in widget.winfo_children():
            bind_mousewheel(child)

    bind_mousewheel(sidebar)
    
    # Show welcome page initially
    show_artifact_welcome_page(content_frame)