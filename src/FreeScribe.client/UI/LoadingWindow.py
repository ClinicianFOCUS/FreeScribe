import tkinter as tk
from tkinter import ttk
from utils.file_utils import get_file_path
import utils.system
import UI.Helpers


class LoadingWindow:
    """
    A class to create and manage an animated processing popup window.

    This class creates a popup window with an animated progress bar to indicate
    ongoing processing and a cancel button to abort the operation.

    :param parent: The parent window for this popup
    :type parent: tk.Tk or tk.Toplevel or None
    :param title: The title of the popup window
    :type title: str
    :param initial_text: The initial text to display in the popup
    :type initial_text: str
    :param on_cancel: Callback function to execute when cancel is pressed
    :type on_cancel: callable or None
    :param note_text: Optional note text to display below the initial text
    :type note_text: str or None

    :ivar popup: The main popup window
    :type popup: tk.Toplevel
    :ivar popup_label: The label widget containing the text
    :type popup_label: tk.Label
    :ivar cancelled: Flag indicating if the operation was cancelled
    :type cancelled: bool

    Example
    -------
    >>> root = tk.Tk()
    >>> processing = LoadingWindow(root, title="Processing", initial_text="Loading", note_text="Note: This may take some time.")
    >>> # Do some work here
    >>> if not processing.cancelled:
    ...     # Complete the operation
    >>> processing.destroy()
    """

    MACOS_SIZE = (300, 125)
    WINDOWS_SIZE = (280, 115)
    NOTE_OFFSET = (80, 75)

    def __init__(
        self,
        parent=None,
        title="Processing",
        initial_text="Loading",
        on_cancel=None,
        note_text=None,
    ):
        """
        Initialize the processing popup window.

        :param parent: Parent window for this popup
        :type parent: tk.Tk or tk.Toplevel or None
        :param title: Title of the popup window
        :type title: str
        :param initial_text: Initial text to display
        :type initial_text: str
        :param on_cancel: Callback function to execute when cancel is pressed
        :type on_cancel: callable or None
        :param note_text: Optional note text to display below the initial text
        :type note_text: str or None
        """
        try:
            self.title = title
            self.initial_text = initial_text
            self.note_text = note_text
            self.parent = parent
            self.on_cancel = on_cancel
            self.cancelled = False

            self.popup = tk.Toplevel(parent)
            self.popup.title(title)

            # Default windows size
            size = (
                LoadingWindow.MACOS_SIZE
                if utils.system.is_macos()
                else LoadingWindow.WINDOWS_SIZE
            )

            if note_text:
                size = (
                    size[0] + LoadingWindow.NOTE_OFFSET[0],
                    size[1] + LoadingWindow.NOTE_OFFSET[1],
                )

            self.popup.geometry(f"{size[0]}x{size[1]}")

            UI.Helpers.set_window_icon(self.popup)

            if parent:
                # Center the popup window on the parent window
                parent.update_idletasks()
                x = (
                    parent.winfo_x()
                    + (parent.winfo_width() - self.popup.winfo_reqwidth()) // 2
                )
                y = (
                    parent.winfo_y()
                    + (parent.winfo_height() - self.popup.winfo_reqheight()) // 2
                )
                self.popup.geometry(f"+{x}+{y}")
                self.popup.transient(parent)

                # Disable the parent window
                UI.Helpers.disable_parent_window(parent, self.popup)

            # Use label and progress bar
            self.label = tk.Label(self.popup, text=initial_text)
            self.label.pack(pady=(10, 5))
            self.progress = ttk.Progressbar(self.popup, mode="indeterminate")
            self.progress.pack(padx=20, pady=(0, 10), fill="x")
            self.progress.start()

            # Add note text if provided
            if note_text:
                font_size = 11 if utils.system.is_macos() else 9
                self.note_label = tk.Label(
                    self.popup,
                    text=note_text,
                    wraplength=350,
                    justify="center",
                    font=("TkDefaultFont", font_size),
                    fg="#262525",
                )
                self.note_label.pack(pady=(0, 10))

            # Add cancel button
            self.cancel_button = ttk.Button(
                self.popup, text="Cancel", command=self._handle_cancel
            )
            self.cancel_button.pack(pady=(7, 5))

            # Not Resizable
            self.popup.resizable(False, False)

            # Disable closing of the popup manually
            self.popup.protocol("WM_DELETE_WINDOW", lambda: None)
        except Exception:
            # Enable the window on exception
            if parent:
                UI.Helpers.enable_parent_window(parent, self.popup)
            raise

    def _handle_cancel(self):
        """
        Internal method to handle cancel button press.
        Sets the cancelled flag and calls the user-provided callback if any.
        """
        self.cancelled = True
        if callable(self.on_cancel):
            try:
                self.on_cancel()
            except Exception:
                self.destroy()

        self.destroy()

    def destroy(self):
        """
        Clean up and destroy the popup window.

        This method performs the following cleanup operations:
        1. Stops the progress bar animation
        2. Re-enables the parent window
        3. Destroys the popup window

        Note
        ----
        This method should be called when you want to close the popup window,
        rather than destroying the window directly.

        Example
        -------
        >>> popup = LoadingWindow()
        >>> # Do some processing
        >>> popup.destroy()  # Properly clean up and close the window
        """
        if self.popup:
            # Enable the parent window
            if self.parent:
                UI.Helpers.enable_parent_window(self.parent, self.popup)

            if self.progress.winfo_exists():
                self.progress.stop()

            if self.popup.winfo_exists():
                self.popup.destroy()
