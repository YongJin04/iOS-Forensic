import tkinter as tk
from tkinter import ttk
from gui.components.display_device_info import *
from gui.components.display_browser import *
from gui.components.display_message import *
from gui.components.display_contacts import *
from gui.components.display_photos_media import *
from gui.components.display_call_history import *
from gui.components.display_sms import *  # Added SMS display module -Liqueur
from gui.components.display_calendar import *  # Added Calendar display module -Liqueur
from gui.components.display_bluetooth import *
from gui.components.display_user_account import *
from backup_analyzer.build_tree import *

def create_artifact_analysis_options(parent, backup_path_var, colors):
    """Create artifact analysis options."""
    main_frame = ttk.Frame(parent)
    main_frame.pack(fill="both", expand=True)
    
    # Left sidebar - artifact category
    sidebar = ttk.Frame(main_frame, style="Sidebar.TFrame", padding=10)
    sidebar.pack(side="left", fill="y", padx=(0, 10))
    
    # Category title
    ttk.Label(sidebar, text="Artifact Categories", style="SidebarHeader.TLabel").pack(anchor="w", pady=(0, 10))
    
    # Create right content area (pre-created here)
    content_frame = ttk.Frame(main_frame, style="Content.TFrame", padding=10)
    content_frame.pack(side="right", fill="both", expand=True)

    # Create category buttons
    categories = [
        {"name": "Device Info", "icon": "📱", "command": lambda: display_device_info(content_frame, backup_path_var.get())},
        {"name": "User Account", "icon": "👤", "command": lambda: display_user_account(content_frame, backup_path_var.get())},
        {"name": "Browser", "icon": "🌐", "command": lambda: display_browser(content_frame, backup_path_var.get())},
        {"name": "KakaoTalk", "icon": "💬", "command": lambda: display_messages(content_frame, backup_path_var.get())},
        {"name": "Contacts", "icon": "📗", "command": lambda: display_contacts(content_frame, backup_path_var.get())},
        {"name": "Call History", "icon": "📞", "command": lambda: display_call_history(content_frame, backup_path_var.get())},  # Added new category
        {"name": "SMS", "icon": "✉️", "command": lambda: display_sms(content_frame, backup_path_var.get())},  # Added SMS category
        {"name": "Photos & Media", "icon": "🖼️", "command": lambda: display_photos_media(content_frame, backup_path_var.get())},
        {"name": "Calendar", "icon": "📅", "command": lambda: display_calendar(content_frame, backup_path_var.get())},  # Added Calrendar category
        {"name": "Gallery", "icon": "🖼️", "command": lambda: display_photos_media(content_frame, backup_path_var.get())},
        {"name": "Bluetooth", "icon": "🔵", "command": lambda: display_bluetooth(content_frame, backup_path_var.get())},
    ]
    
    category_buttons = []
    selected_category = tk.StringVar()
    
    # Button creation function
    def create_category_button(category, index):
        btn_frame = ttk.Frame(sidebar, style="SidebarItem.TFrame", padding=5)
        btn_frame.pack(fill="x", pady=2)
        
        # Selection indicator
        indicator = ttk.Frame(btn_frame, width=3, style="Indicator.TFrame")
        indicator.pack(side="left", fill="y", padx=(0, 5))
        
        # Button with icon and name
        btn = ttk.Button(
            btn_frame,
            text=f"{category['icon']} {category['name']}",
            style="Sidebar.TButton",
            command=lambda: activate_category(index, category)
        )
        btn.pack(fill="x", expand=True)
        return {"button": btn, "indicator": indicator, "frame": btn_frame}
    
    # Category activation function
    def activate_category(index, category):
        selected_category.set(category["name"])
        # Apply inactive style to all buttons
        for i, btn_data in enumerate(category_buttons):
            if i == index:
                btn_data["frame"].configure(style="SidebarItemActive.TFrame")
                btn_data["indicator"].configure(style="IndicatorActive.TFrame")
            else:
                btn_data["frame"].configure(style="SidebarItem.TFrame")
                btn_data["indicator"].configure(style="Indicator.TFrame")
        
        # Display content corresponding to category
        if category["command"]:
            category["command"]()  # Execute function for selected category
    
    # Create category buttons
    for i, category in enumerate(categories):
        button_data = create_category_button(category, i)
        category_buttons.append(button_data)
    
    # Show initial page
    show_artifact_welcome_page(content_frame)
    
    return {
        "sidebar": sidebar, 
        "content_frame": content_frame,
        "category_buttons": category_buttons,
        "selected_category": selected_category
    }

def show_artifact_welcome_page(content_frame):
    """Display the artifact analysis start page."""
    # Clear existing widgets
    for widget in content_frame.winfo_children():
        widget.destroy()
    
    # Display welcome message and guide
    welcome_frame = ttk.Frame(content_frame, style="Card.TFrame", padding=20)
    welcome_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    ttk.Label(welcome_frame, text="iOS Backup Artifact Analysis", style="CardHeader.TLabel").pack(pady=(0, 20))
    ttk.Label(welcome_frame, text="Select an artifact category on the left to begin analysis.", 
              style="CardText.TLabel", wraplength=400).pack(pady=10)
    
    # Icon descriptions
    icon_frame = ttk.Frame(welcome_frame)
    icon_frame.pack(pady=20)
    
    icons = [
        {"icon": "📱", "text": "Device Info"},
        {"icon": "💬", "text": "KakaoTalk"},
        {"icon": "👤", "text": "Contacts"},
        {"icon": "🖼️", "text": "Gallery"}
    ]
    
    for icon_data in icons:
        icon_item = ttk.Frame(icon_frame)
        icon_item.pack(side="left", padx=15)
        ttk.Label(icon_item, text=icon_data["icon"], font=("Arial", 24)).pack(anchor="center")
        ttk.Label(icon_item, text=icon_data["text"], style="CardText.TLabel").pack(anchor="center")
