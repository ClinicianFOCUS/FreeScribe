import tkinter as tk
from tkinter import scrolledtext

import UI.Helpers
from utils.file_utils import get_file_path

class ScrubWindow:
    def __init__(self, parent, cleaned_message, onProceed, onCancel):
        """
        Initialize the ScrubWindow.

        Args:
            parent (tk.Tk or tk.Toplevel): The parent window.
            cleaned_message (str): The message to be displayed in the text area.
            onProceed (function): The callback function to be called when the Proceed button is clicked.
            onCancel (function): The callback function to be called when the Cancel button is clicked.
        """
        # Create a new top-level window
        popup = tk.Toplevel(parent)
        popup.title("Scrub PHI Prior to GPT")
        popup.grab_set()  # Make the popup modal
        UI.Helpers.set_window_icon(popup)

        # Create a scrolled text area
        text_area = scrolledtext.ScrolledText(popup, height=20, width=80)
        text_area.pack(padx=10, pady=10)
        text_area.insert(tk.END, cleaned_message)  # Insert the cleaned message into the text area

        def on_proceed():
            """
            Handle the Proceed button click event.
            """
            edited_text = text_area.get("1.0", tk.END).strip()  # Get the edited text from the text area
            popup.destroy()  # Close the popup window
            onProceed(edited_text)  # Call the onProceed callback with the edited text

        # Create the Proceed button
        proceed_button = tk.Button(popup, text="Proceed", command=on_proceed)
        proceed_button.pack(side=tk.RIGHT, padx=10, pady=10)

        def on_cancel():
            """
            Handle the Cancel button click event.
            """
            popup.destroy()  # Close the popup window
            onCancel()  # Call the onCancel callback

        # Create the Cancel button
        cancel_button = tk.Button(popup, text="Cancel", command=on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=10, pady=10)