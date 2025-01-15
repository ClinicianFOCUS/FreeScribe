import sys
import tkinter as tk


def set_window_icon(window, icon_path):
    """
    Set a window icon on the given window.
    """
    if sys.platform == 'linux':
        window.tk.call('wm', 'iconphoto', window._w, tk.PhotoImage(icon_path))
    else:
        window.iconbitmap(icon_path)


def disable_window(window):
    if sys.platform == 'linux':
        window.grab_set()
    else:
        window.wm_attributes('-disabled', True)
