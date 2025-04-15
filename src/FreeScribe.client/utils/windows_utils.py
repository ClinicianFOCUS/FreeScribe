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

import ctypes
import logging
import subprocess
import time

from utils.decorators import windows_only

logger = logging.getLogger(__name__)


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
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

    GWL_STYLE = -16
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000

    # Get current window style
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)

    # Remove minimize and maximize box styles
    style &= ~WS_MINIMIZEBOX
    style &= ~WS_MAXIMIZEBOX

    # Apply the new style
    # 0x0027 = SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAME
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
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
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

    GWL_STYLE = -16
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000

    # Get current window style
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)

    # Add minimize and maximize box styles back
    style |= WS_MINIMIZEBOX
    style |= WS_MAXIMIZEBOX

    # Apply the new style
    # 0x0027 = SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAME
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                               0x0027)


def bring_to_front(app_name: str) -> bool:
    """
    Bring the window with the given handle to the front on Windows.

    Args:
        app_name (str): The name of the application window to bring to the front

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        U32DLL = ctypes.WinDLL('user32')
        SW_SHOW = 5
        hwnd = U32DLL.FindWindowW(None, app_name)
        if not hwnd:
            return False
        U32DLL.ShowWindow(hwnd, SW_SHOW)
        U32DLL.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        logger.error(f"Failed to bring window to front: {e}")
        return False


def kill_with_admin_privilege(pids: list[int]) -> bool:
    """
    Attempt to kill processes with elevated administrator privileges on Windows.

    Args:
        pids (list[int]): List of process IDs to terminate

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not pids:
            return True

        pids_str = [str(pid) for pid in pids]
        logger.info(f"Killing {pids_str=} with administrator privileges")

        # Build the taskkill command
        taskkill_args = f'/c taskkill /F /PID {" /PID ".join(pids_str)}'
        logger.info(f"Running command: powershell Start-Process cmd -ArgumentList \"{taskkill_args}\" -Verb runAs")

        # Run the command with admin privileges
        proc = subprocess.run(
            [
                "powershell",
                "Start-Process",
                "cmd",
                "-ArgumentList",
                f'"{taskkill_args}"',
                "-Verb",
                "runAs"
            ],
            check=True
        )

        logger.info(f"Killed {pids_str=} with administrator privileges, Exit code {proc.returncode=}")
        # wait a little bit for windows to clean the proc list
        time.sleep(0.5)
        return True
    except Exception as e:
        logger.exception(f"Failed to kill processes with admin privileges: {e}")
        return False

    
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