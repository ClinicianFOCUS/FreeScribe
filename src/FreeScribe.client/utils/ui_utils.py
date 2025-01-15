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
