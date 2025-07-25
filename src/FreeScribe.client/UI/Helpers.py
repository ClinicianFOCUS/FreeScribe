"""
This software is released under the AGPL-3.0 license
Copyright (c) 2023-2025 Braedon Hendy

Further updates and packaging added in 2024-2025 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform". 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students (Software Developers) - 
Alex Simko, Pemba Sherpa, Naitik Patel, Yogesh Kumar and Xun Zhong.
"""

import utils.system
import utils.file_utils
import tkinter as tk
from utils.log_config import logger

def enable_parent_window(parent, child_window = None):
    """
    Enable the parent window after a child window has been closed.
    
    :param parent: The parent window to enable
    :type parent: tk.Tk or tk.Toplevel
    :param child_window: The child window that was closed
    :type child_window: tk.Toplevel
    """
    if utils.system.is_windows():
        parent.wm_attributes('-disabled', False)
    elif utils.system.is_macos() or utils.system.is_linux():
        if child_window:
            child_window.grab_release()
        else:
            logger.warning("Child window not provided")


def disable_parent_window(parent, child_window = None):
    """
    Disable the parent window when a child window is opened.
    
    :param parent: The parent window to disable
    :type parent: tk.Tk or tk.Toplevel
    :param child_window: The child window that is opened
    :type child_window: tk.Toplevel
    """
    if utils.system.is_windows():
        parent.wm_attributes('-disabled', True)
    elif utils.system.is_macos() or utils.system.is_linux():
        if child_window:
            child_window.transient(parent)
            child_window.grab_set()
            child_window.attributes('-topmost', True)
        else:
            logger.warning("Child window not provided")


def set_window_icon(window):
    """
    Set a window icon on the given window.
    """
    try:
        if utils.system.is_linux():
            icon_path = utils.file_utils.get_file_path('assets', 'logo.png')
            window.iconphoto(True, tk.PhotoImage(file=icon_path))
        else:
            icon_path = utils.file_utils.get_file_path('assets', 'logo.ico')
            window.iconbitmap(icon_path)
    except Exception as e:
        logger.exception(f"Failed to set window icon. This was handled gracefully using default. The error below is just the call stack: {e}")

def center_window_to_parent(window, parent):
    """
    Center the given window to the parent window.
    
    :param window: The window to center
    :type window: tk.Toplevel or tk.Tk
    :param parent: The parent window to center to
    :type parent: tk.Toplevel or tk.Tk
    """
    window.update_idletasks()  # Ensure the window has its size calculated
    parent.update_idletasks()  # Ensure the parent window has its size calculated
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (window.winfo_width() // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (window.winfo_height() // 2)
    window.geometry(f"+{x}+{y}")