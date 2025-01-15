import sys
import tkinter as tk
from utils.file_utils import get_file_path


def set_window_icon(window):
    """
    Set a window icon on the given window.
    """
    if sys.platform == 'linux':
        icon_path = get_file_path('assets', 'logo.png')
        window.iconphoto(True, tk.PhotoImage(file=icon_path))
    else:
        icon_path = get_file_path('assets', 'logo.ico')
        window.iconbitmap(icon_path)


def disable_parent_window(parent, child):
    if sys.platform == 'linux':
        child.transient(parent)
        child.grab_set()
        child.focus_force()
    else:
        parent.wm_attributes('-disabled', True)


def enable_parent_window(parent, child):
    if sys.platform == 'linux':
        child.grab_release()  # Release the grab
        parent.grab_set()
        parent.focus_force()
    else:
        parent.wm_attributes('-disabled', False)
