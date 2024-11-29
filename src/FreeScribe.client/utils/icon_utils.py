
import sys
import tkinter as tk
from utils.file_utils import get_file_path

def set_logo(root) :
    if sys.platform == "darwin":
        icon_path = get_file_path('assets', 'logo.gif')
        icon_image = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, icon_image)
    else:
        icon_path = get_file_path('assets', 'logo.ico')
        root.iconbitmap(icon_path)
