import tkinter as tk  # Tkinter library for GUI development (standard library)
from tkinter import ttk  # Module that provides themed widget set for Tkinter
import sys
import os

from gui.events_utils import (
    browse_backup_path,
    toggle_password_entry,
    update_file_list_from_backup_tree_click,
    update_backup_tree_from_file_list_double_click
)
from gui.extract_file import show_file_list_context_menu
from gui.load_backup_utils import load_backup  # Function to load backup data
from artifact_analyzer.device.device_info import show_device_info  # Function to show device info

def start_gui():
    rootWindow = tk.Tk()  # Create the base window object based on Tk
    rootWindow.title("iOS Forensic Viewer")  # Set the window title

    # Set the taskbar icon for Windows OS
    icon_path_ico = "gui/icon/pay1oad.ico"
    if sys.platform == "win32":  # If running in Windows OS environment
        import ctypes  # Module for loading C-compatible DLLs and libraries on Windows OS
        if os.path.exists(icon_path_ico):  # Check if the icon file actually exists
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("iOS.Forensic.Viewer")
            rootWindow.iconbitmap(icon_path_ico)  # Set the window icon

    # Set the window size
    rootWindow.minsize(900, 600)         # Set the minimum size of the window
    rootWindow.geometry("900x600")       # Set the initial window size to 900x600

    setup_gui(rootWindow)                # Call setup_gui function to build the GUI layout

    rootWindow.mainloop()                # Start the event message loop to wait for user input

def setup_gui(rootWindow):
    # Main container frame with padding
    frame = ttk.Frame(rootWindow, padding=15)
    frame.pack(fill="both", expand=True)

    # Initialize Input Variables
    backup_path_var = tk.StringVar()    # Backup Directory Path
    enable_pw_var = tk.IntVar(value=0)  # Enable Password Flag (0: disabled (Default), 1: enabled)
    password_var = tk.StringVar()       # Backup Decrypt Password

    # Create "Select Backup Directory" frame and its widgets
    select_backup_widgets = create_select_backup_dir_frame(frame, backup_path_var)
    
    # Create "Backup Decrypt Password" frame and its widgets
    pw_widgets = create_backup_decrypt_password_frame(frame, password_var, enable_pw_var)
    pw_widgets['enable_pw_check'].configure(command=lambda: toggle_password_entry(enable_pw_var, pw_widgets['password_entry'], password_var))

    # Create "Artifact Analysis Bar" frame and its widgets
    artifact_widgets = create_artifact_analysis_bar(frame, backup_path_var)

    # Create PanedWindow for "Backup Tree" and "File List" (horizontal split)
    paned = ttk.PanedWindow(frame, orient="horizontal")
    paned.pack(fill="both", expand=True)

    backup_tree_widgets = create_backup_tree_frame(paned)
    paned.add(backup_tree_widgets['backup_tree_frame'], weight=2)  # Add tree frame to paned window with weight 2
    
    file_list_widgets = create_file_list_frame(paned)
    paned.add(file_list_widgets['file_list_frame'], weight=8)  # Add file list frame to paned window with weight 8

    select_backup_widgets['browse_button'].configure(command=lambda: browse_backup_path(backup_path_var, pw_widgets['password_entry'], password_var, enable_pw_var))  # Update the commands for buttons that depend on widgets created later
    select_backup_widgets['load_backup_button'].configure(  # Update the commands for buttons that depend on widgets created later
        command=lambda: load_backup(
            backup_path_var.get(),
            password_var.get(),
            backup_tree_widgets['backup_tree'],
            enable_pw_var,
            file_list_widgets['file_list_tree']
        )
    )

    # Bind right-click event on the "File List" treeview to show context menu
    file_list_widgets['file_list_tree'].bind(
        "<Button-3>",  # Right mouse button click event
        lambda event: show_file_list_context_menu(
            event,                                      # Event object
            file_list_widgets['file_list_tree'],        # Target Treeview widget (File List)
            backup_path_var.get()                       # Backup path (passed to context menu function)
        )
    )

    """
     - Bind Treeview events (execute corresponding functions on each event)
     - Treeview widgets, by default, toggle open when the "Double-Button-1" event occurs.
    """
    # Function that updates the "File List" when an item in the "Backup Tree" is one-clicked (selecting a file or directory).
    backup_tree_widgets['backup_tree'].bind("<<TreeviewSelect>>", lambda event: update_file_list_from_backup_tree_click(event, file_list_widgets['file_list_tree'], backup_tree_widgets['backup_tree']))
    # Function that updates the "Backup Tree" when an item in the "File List" is double-clicked (navigating the directory hierarchy).
    file_list_widgets['file_list_tree'].bind("<Double-Button-1>", lambda event: update_backup_tree_from_file_list_double_click(event, file_list_widgets['file_list_tree'], backup_tree_widgets['backup_tree']))

def create_select_backup_dir_frame(parent, backup_path_var):
    """ Create Select Backup Directory Frame. """
    select_backup_dir_frame = ttk.Frame(parent)
    select_backup_dir_frame.pack(fill="x", pady=5)
    select_backup_dir_frame.grid_columnconfigure(1, weight=1)  # Dynamically adjust child widget size when parent frame changes

    # Label: "Backup Directory:"
    ttk.Label(select_backup_dir_frame, text="Backup Directory:", font=("Helvetica", 10)).grid(row=0, column=0, padx=5, pady=2, sticky="w")

    # Entry: "Backup Path"
    path_entry = ttk.Entry(select_backup_dir_frame, textvariable=backup_path_var)
    path_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

    # Button Frame for "Browse" and "Load Backup" buttons
    button_frame = ttk.Frame(select_backup_dir_frame)
    button_frame.grid(row=0, column=2, padx=5, pady=2, sticky="e")
    button_frame.grid_columnconfigure(0, weight=1)

    # Button: "Browse"
    browse_button = ttk.Button(
        button_frame,             # Parent Frame
        text="Browse",            # Text
        command=lambda: None      # Placeholder: will be updated later to call browse_backup_path function
    )
    browse_button.pack(side="left", padx=2)

    # Button: "Load Backup"
    load_backup_button = ttk.Button(
        button_frame,             # Parent Frame
        text="Load Backup",       # Text
        command=lambda: None,     # Placeholder: will be updated later to call load_backup function
        style="large.TButton"
    )
    load_backup_button.pack(side="left", padx=2)

    return {
        'select_backup_dir_frame': select_backup_dir_frame,
        'path_entry': path_entry,
        'browse_button': browse_button,
        'load_backup_button': load_backup_button
    }

def create_backup_decrypt_password_frame(parent, password_var, enable_pw_var):
    """ Create Backup Decrypt Password Frame. """
    pw_frame = ttk.Frame(parent)
    pw_frame.pack(fill="x", pady=5)
    pw_frame.grid_columnconfigure(1, weight=1)

    # Button: "Enable Password"
    enable_pw_check = ttk.Checkbutton(
        pw_frame,               # Parent Frame
        text="Enable Password", # Text
        variable=enable_pw_var, # Connects check state to enable_pw_var variable
        command=lambda: None    # Placeholder: will be updated later to call toggle_password_entry function
    )
    enable_pw_check.pack(side="left", padx=5)

    # Label: "Password"
    ttk.Label(pw_frame, text="Password:", font=("Helvetica", 10)).pack(side="left", padx=5)

    # Entry: "Backup Password"
    password_entry = ttk.Entry(pw_frame, textvariable=password_var, width=30, show="*")
    password_entry.pack(side="left", padx=5)
    password_entry.config(state="disabled")  # Default is "disabled"

    return {
        'pw_frame': pw_frame,
        'enable_pw_check': enable_pw_check,
        'password_entry': password_entry
    }

def create_artifact_analysis_bar(parent, backup_path_var):
    """ Create Artifact Analysis Bar. """
    device_info_frame = ttk.Frame(parent)
    device_info_frame.pack(fill="x", pady=5)

    # Button: "Device Info"
    device_info_button = ttk.Button(
        device_info_frame,           # Parent Frame
        text="Device Info",          # Text
        command=lambda: show_device_info(backup_path_var.get())  # If pressed, call show_device_info function
    )
    device_info_button.pack(side="left", padx=5)

    return {
        'device_info_frame': device_info_frame,
        'device_info_button': device_info_button
    }

def create_backup_tree_frame(parent):
    """ Create Backup Tree Frame. """
    backup_tree_frame = ttk.Frame(parent)
    
    # Create Treeview widget to display backup folder structure
    backup_tree = ttk.Treeview(backup_tree_frame)
    backup_tree.heading("#0", text="Backup Tree", anchor="w")  # Set treeview header (left aligned)
    backup_tree.pack(side="left", fill="both", expand=True)

    # Create vertical scrollbar for the treeview (handles vertical scrolling)
    backup_tree_scrollbar = ttk.Scrollbar(backup_tree_frame, orient="vertical", command=backup_tree.yview)
    backup_tree_scrollbar.pack(side="right", fill="y")
    backup_tree.configure(yscrollcommand=backup_tree_scrollbar.set)

    return {
        'backup_tree_frame': backup_tree_frame,
        'backup_tree': backup_tree,
        'backup_tree_scrollbar': backup_tree_scrollbar
    }

def create_file_list_frame(parent):
    """ Create File List Frame. """
    file_list_frame = ttk.Frame(parent)

    # Create Treeview widget to display file list
    file_list_tree = ttk.Treeview(file_list_frame)
    file_list_tree.heading("#0", text="File List", anchor="w")  # Set treeview header (left aligned)
    file_list_tree.pack(side="left", fill="both", expand=True)

    # Create vertical scrollbar for the file list (handles vertical scrolling)
    file_list_scrollbar = ttk.Scrollbar(file_list_frame, orient="vertical", command=file_list_tree.yview)
    file_list_scrollbar.pack(side="right", fill="y")
    file_list_tree.configure(yscrollcommand=file_list_scrollbar.set)

    return {
        'file_list_frame': file_list_frame,
        'file_list_tree': file_list_tree,
        'file_list_scrollbar': file_list_scrollbar
    }
