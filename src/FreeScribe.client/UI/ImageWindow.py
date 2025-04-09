import tkinter as tk
from tkinter import Toplevel, messagebox
from PIL import Image, ImageTk
from utils.file_utils import get_file_path

class ImageWindow:
    """A window to display an image with scrollbars and zoom functionality.
    
    This class creates a scrollable window that displays an image file. It supports:
    - Vertical and horizontal scrolling
    - Mouse wheel navigation
    - Automatic window sizing and centering
    - Error handling for missing image files
    
    :param parent: The parent tkinter widget
    :type parent: tk.Widget
    :param title: Window title text
    :type title: str
    :param image_path: Path to the image file to display
    :type image_path: str
    """
    def __init__(self, parent, title, image_path):
        """Initialize the ImageWindow.
        
        Creates a new window, loads the specified image, and sets up scrollable canvas.
        Handles errors if image file is not found.
        
        :param parent: The parent tkinter widget
        :type parent: tk.Widget
        :param title: Window title text
        :type title: str
        :param image_path: Path to the image file to display
        :type image_path: str
        """
        try:
            # Create window and load image
            self.window = Toplevel(parent)
            self.window.title(title)
            self.window.iconbitmap(get_file_path('assets', 'logo.ico'))
            
            # Load image
            self.image = Image.open(image_path)
            self.photo = ImageTk.PhotoImage(self.image)
            
            # Create canvas with scrollbars
            canvas_frame = tk.Frame(self.window)
            canvas_frame.pack(fill="both", expand=True)
            
            # Create canvas
            self.canvas = tk.Canvas(canvas_frame)
            self.canvas.grid(row=0, column=0, sticky="nsew")
            
            # Add scrollbars
            v_scroll = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
            v_scroll.grid(row=0, column=1, sticky="ns")
            
            h_scroll = tk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
            h_scroll.grid(row=1, column=0, sticky="ew")
            
            # Configure canvas
            self.canvas.configure(
                yscrollcommand=v_scroll.set,
                xscrollcommand=h_scroll.set,
                scrollregion=(0, 0, self.image.width, self.image.height)
            )
            
            # Add image to canvas
            self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
            
            # Configure grid weights
            canvas_frame.grid_rowconfigure(0, weight=1)
            canvas_frame.grid_columnconfigure(0, weight=1)
            
            # Bind mouse wheel events to canvas
            self.canvas.bind("<MouseWheel>", self._on_mousewheel)
            self.canvas.bind("<Shift-MouseWheel>", self._on_horizontal_scroll)
            
            # Make sure canvas can receive focus
            self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
            
            # Set initial window size
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            width = min(self.image.width, screen_width - 100)
            height = min(self.image.height, screen_height - 100)
            self.window.geometry(f"{width}x{height}")
            
            # Center window
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.window.geometry(f"+{x}+{y}")
            
            # Bind window close to escape key
            self.window.bind('<Escape>', lambda e: self.window.destroy())
            
        except FileNotFoundError:
            messagebox.showerror("Error", f"Image file not found: {image_path}")
            if hasattr(self, 'window'):
                self.window.destroy()

    def _on_mousewheel(self, event):
        """Handle vertical scrolling with mouse wheel.
        
        Supports both Windows/Mac and Linux mouse wheel events.
        
        :param event: The mouse wheel event
        :type event: tk.Event
        :return: "break" to prevent event propagation
        :rtype: str
        """
        if event.num == 4:  # Linux scroll up
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:  # Linux scroll down
            self.canvas.yview_scroll(1, "units")
        else:  # Windows/Mac
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
        return "break"

    def _on_horizontal_scroll(self, event):
        """Handle horizontal scrolling with mouse wheel.
        
        Supports both Windows/Mac and Linux mouse wheel events when Shift is held.
        
        :param event: The mouse wheel event
        :type event: tk.Event
        :return: "break" to prevent event propagation
        :rtype: str
        """
        if event.num == 4:  # Linux scroll left
            self.canvas.xview_scroll(-1, "units")
        elif event.num == 5:  # Linux scroll right
            self.canvas.xview_scroll(1, "units")
        else:  # Windows/Mac
            self.canvas.xview_scroll(-1 * (event.delta // 120), "units")
        return "break"
