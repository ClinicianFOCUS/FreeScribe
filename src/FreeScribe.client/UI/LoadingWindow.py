import tkinter as tk
from tkinter import ttk
from utils.file_utils import get_file_path
from utils.log_config import logger
import utils.system
import UI.Helpers
import time

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
        self.title = title
        self.initial_text = initial_text
        self.note_text = note_text
        self.parent = parent
        self.on_cancel = on_cancel
        self.cancelled = False
        self.ui_built = False
    
        if self.parent:
            self.parent.after(0, self.build_ui)

    def build_ui(self):
        try:
            logger.debug("Building LoadingWindow UI")
            self.popup = tk.Toplevel(self.parent)
            self.popup.title(self.title)
            # Adjust geometry based on whether note_text is provided
            if self.note_text:
                self.popup.geometry("360x180")  # Increased height for note text
            else:
                self.popup.geometry("280x105")  # Default height
            self.popup.iconbitmap(get_file_path('assets','logo.ico'))

            if self.parent:
                # Center the popup window on the parent window
                self.parent.update_idletasks()
                x = (
                    self.parent.winfo_x()
                    + (self.parent.winfo_width() - self.popup.winfo_reqwidth()) // 2
                )
                y = (
                    self.parent.winfo_y()
                    + (self.parent.winfo_height() - self.popup.winfo_reqheight()) // 2
                )
                self.popup.geometry(f"+{x}+{y}")
                self.popup.transient(self.parent)
                
                # Disable the parent window
                UI.Helpers.disable_parent_window(self.parent, self.popup)

            # Use label and progress bar
            self.label = tk.Label(self.popup, text=self.initial_text)
            self.label.pack(pady=(10,5))
            self.progress = ttk.Progressbar(self.popup, mode='indeterminate')
            self.progress.pack(padx=20, pady=(0,10), fill='x')
            self.progress.start()

            # Add note text if provided
            if self.note_text:
                font_size = 11 if utils.system.is_macos() else 9
                self.note_label = tk.Label(
                    self.popup,
                    text=self.note_text,
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
            
            logger.debug("LoadingWindow UI built successfully")
            self.ui_built = True
        except Exception:
            logger.exception("Error creating LoadingWindow")
            # Enable the window on exception
            if self.parent:
                UI.Helpers.enable_parent_window(self.parent, self.popup)
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
                logger.exception("Error in on_cancel callback")
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
        # wait for the UI to be built
        def _destroy_ui():
            start_time = time.time()
            logger.debug("Waiting for LoadingWindow UI to be built")
            while not self.ui_built:
                elapsed_time = time.time() - start_time
                if int(elapsed_time) % 2 == 0 or elapsed_time < 1:
                    logger.info(f"Waiting for LoadingWindowUI to build (elapsed={elapsed_time}s, built={self.ui_built})")
                time.sleep(0.1)
            
            logger.debug("LoadingWindow UI is built, proceeding to destroy it")
            if self.popup:
                # Enable the parent window
                if self.parent:
                    logger.debug("Enabling parent window")
                    UI.Helpers.enable_parent_window(self.parent, self.popup)

                if hasattr(self, 'progress') and self.progress:
                    logger.debug("Stopping progress bar animation")
                    if self.progress.winfo_exists():
                        # Stop the progress bar animation
                        self.progress.stop()

                if self.popup.winfo_exists():
                    logger.debug("Destroying popup window")
                    self.popup.destroy()

        if self.parent and hasattr(self.parent, 'after'):
            logger.debug("Using parent.after to destroy LoadingWindow UI")
            self.parent.after(0, _destroy_ui)
        else:
            # Call the destroy function directly if parent is not available
            logger.debug("Parent not available, calling _destroy_ui directly")
            _destroy_ui()

