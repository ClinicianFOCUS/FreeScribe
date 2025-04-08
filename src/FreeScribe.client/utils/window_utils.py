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

import tkinter as tk
import platform
from ctypes import windll
from utils.decorators import windows_only

@windows_only
def remove_min_max(window):
    """
    Removes the minimize and maximize buttons from a window's title bar on Windows systems.
    
    This function modifies the window style flags to remove the minimize and maximize
    buttons from the title bar. The function only works on Windows operating systems
    and will print a message and return if called on other platforms.
    
    Args:
        window: A tkinter window object or similar window handle that supports winfo_id()
    
    Returns:
        None
    
    Note:
        This function requires the windll module from ctypes and only works on Windows systems.
        The window style changes are applied immediately.
    """
    hwnd = windll.user32.GetParent(window.winfo_id())

    GWL_STYLE = -16
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000

    # Get current window style
    style = windll.user32.GetWindowLongW(hwnd, GWL_STYLE)

    # Remove minimize and maximize box styles
    style &= ~WS_MINIMIZEBOX
    style &= ~WS_MAXIMIZEBOX

    # Apply the new style
    # 0x0027 = SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAME
    windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                               0x0027)

@windows_only
def add_min_max(window):
    """
    Adds the minimize and maximize buttons to a window's title bar on Windows systems.
    
    This function modifies the window style flags to add the minimize and maximize
    buttons to the title bar. The function only works on Windows operating systems
    and will print a message and return if called on other platforms.
    
    Args:
        window: A tkinter window object or similar window handle that supports winfo_id()
    
    Returns:
        None
    
    Note:
        This function requires the windll module from ctypes and only works on Windows systems.
        The window style changes are applied immediately.
    """
    hwnd = windll.user32.GetParent(window.winfo_id())

    GWL_STYLE = -16
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000

    # Get current window style
    style = windll.user32.GetWindowLongW(hwnd, GWL_STYLE)

    # Add minimize and maximize box styles back
    style |= WS_MINIMIZEBOX
    style |= WS_MAXIMIZEBOX

    # Apply the new style
    # 0x0027 = SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAME
    windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                               0x0027)
    
def _display_center_to_parent(window, parent, width=None, height=None):
    # Get parent window dimensions and position
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()

    # Calculate the position for the settings window
    window_width = width or window.winfo_width()
    window_height = height or window.winfo_height()

    center_x = parent_x + (parent_width - window_width) // 2
    center_y = parent_y + (parent_height - window_height) // 2

    # Apply the calculated position to the settings window
    window.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")