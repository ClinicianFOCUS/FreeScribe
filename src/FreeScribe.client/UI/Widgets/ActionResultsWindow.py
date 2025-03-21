"""
Window for displaying intent action results.
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path
import webbrowser
import os
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ActionResultsWindow:
    """
    Window for displaying intent action results.
    
    This window appears to the right of the main window and shows
    a list of cards containing action results like maps and directions.
    """
    
    def __init__(self, parent: tk.Tk):
        """
        Initialize the action results window.
        
        :param parent: Parent window
        """
        self.parent = parent
        self.window = None
        self.canvas = None
        self.scrollable_frame = None
        self.images = []  # Store image references to prevent garbage collection
        
        # Track window state
        self.is_visible = False
        self.last_parent_geometry = None
        
        self._create_window()
        
        # Bind to parent window events
        self.parent.bind("<Configure>", self._on_parent_moved)
        
    def _create_window(self) -> None:
        """Create the window and its widgets."""
        if self.window is not None:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
                
        self.window = tk.Toplevel(self.parent)
        self.window.title("Action Results")
        self.window.geometry("400x600")
        self.window.resizable(True, True)
        
        # Remove window decorations to make it look more integrated
        self.window.overrideredirect(True)
        
        # Create title bar with close button
        title_bar = ttk.Frame(self.window)
        title_bar.pack(fill="x", padx=0, pady=0)
        
        # Add title
        title_label = ttk.Label(title_bar, text="Action Results", style="CardTitle.TLabel")
        title_label.pack(side="left", padx=10, pady=5)
        
        # Add close button
        close_button = ttk.Label(title_bar, text="✕", cursor="hand2")
        close_button.pack(side="right", padx=10, pady=5)
        close_button.bind("<Button-1>", lambda e: self.hide())
        
        # Add separator below title bar
        ttk.Separator(self.window, orient="horizontal").pack(fill="x")
        
        # Create scrollable frame
        self.canvas = tk.Canvas(self.window)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Bind mouse wheel events
        def _bind_to_mousewheel(event):
            """Bind mouse wheel events when mouse enters a widget."""
            if event.widget == self.canvas:
                return  # Canvas already bound
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            self.canvas.bind_all("<Button-4>", self._on_mousewheel)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel)
            
        def _unbind_from_mousewheel(event):
            """Unbind mouse wheel events when mouse leaves a widget."""
            if event.widget == self.canvas:
                return  # Keep canvas bound
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")
        
        # Bind mouse wheel to canvas permanently
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        
        # Bind enter/leave events to all widgets
        self.scrollable_frame.bind("<Enter>", _bind_to_mousewheel)
        self.scrollable_frame.bind("<Leave>", _unbind_from_mousewheel)
        
        # Create the window in the canvas
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Initially hide the window
        self.window.withdraw()
        
        # Update window position
        self._update_window_position()
        
    def _update_window_position(self) -> None:
        """Update the window position to stay on the right side of parent."""
        if not self.window or not self.is_visible:
            return
            
        try:
            # Get parent window position and size
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            # Calculate position for results window - add 5px gap
            window_x = parent_x + parent_width + 5
            window_y = parent_y
            
            # Set window height to match parent
            self.window.geometry(f"400x{parent_height}+{window_x}+{window_y}")
            
        except (tk.TclError, AttributeError) as e:
            logger.error(f"Error updating window position: {e}")
            
    def _on_parent_moved(self, event: tk.Event) -> None:
        """Handle parent window movement/resize."""
        if not self.window or not self.is_visible:
            return
            
        # Get current parent geometry
        current_geometry = self.parent.geometry()
        
        # Only update if the geometry actually changed
        if current_geometry != self.last_parent_geometry:
            self.last_parent_geometry = current_geometry
            self._update_window_position()
            
        # Ensure our window stays on top
        self.window.lift()
        
    def _open_file(self, file_path: str) -> None:
        """Open a file with the default application."""
        try:
            os.startfile(file_path)
        except AttributeError:  # os.startfile is Windows only
            try:
                import subprocess
                subprocess.run(['xdg-open', file_path])  # Linux
            except:
                webbrowser.open(file_path)  # Fallback
        
    def add_result(self, result: Dict[str, Any]) -> None:
        """
        Add a new action result card to the window.
        
        :param result: Action result data
        """
        # Create card frame
        card = ttk.Frame(self.scrollable_frame, style="Card.TFrame")
        card.pack(fill="x", padx=10, pady=5)
        
        # Bind mouse wheel events to the card and its children
        card.bind("<Enter>", lambda e: self.scrollable_frame.event_generate("<Enter>"))
        card.bind("<Leave>", lambda e: self.scrollable_frame.event_generate("<Leave>"))
        
        # Add header
        header = ttk.Frame(card)
        header.pack(fill="x", padx=5, pady=5)
        
        icon = ttk.Label(header, text=result["ui"]["icon"])
        icon.pack(side="left", padx=5)
        
        title = ttk.Label(header, text=result["display_name"], style="CardTitle.TLabel")
        title.pack(side="left", padx=5)
        
        # Add message
        message = ttk.Label(
            card, 
            # text=result["message"], 
            wraplength=350
        )
        message.pack(fill="x", padx=10, pady=5)
        
        # Handle result based on type
        result_type = result["data"].get("type")
        
        if result_type == "directions":
            # Create clickable link for directions
            directions_link = ttk.Label(
                card,
                text=result["message"],
                cursor="hand2",
                foreground="blue"
            )
            directions_link.pack(pady=0, padx=0)
            directions_link.bind("<Button-1>", lambda e: webbrowser.open(result["data"]["click_url"]))
            
            # If there's a map image, show it below the link
            if "additional_info" in result["data"] and "map_image_path" in result["data"]["additional_info"]:
                try:
                    image = Image.open(result["data"]["additional_info"]["map_image_path"])
                    image = image.resize((350, 350), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    self.images.append(photo)  # Prevent garbage collection
                    
                    map_label = ttk.Label(card, image=photo)
                    map_label.pack(pady=5)
                except Exception as e:
                    print(f"Error loading map image: {e}")
                    
        elif "additional_info" in result["data"]:
            info = result["data"]["additional_info"]
            
            # Handle map image if available
            if "map_image_path" in info:
                try:
                    image = Image.open(info["map_image_path"])
                    image = image.resize((350, 350), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    self.images.append(photo)  # Prevent garbage collection
                    
                    # Create frame for map and controls
                    map_frame = ttk.Frame(card)
                    map_frame.pack(pady=5)
                    
                    # Add map image
                    map_label = ttk.Label(
                        map_frame,
                        image=photo,
                        cursor="hand2"  # Always show hand cursor for clickable items
                    )
                    map_label.pack(pady=5)
                    
                    # Add click handler for map type
                    map_label.bind("<Button-1>", lambda e: self._open_file(info["map_image_path"]))
                    instruction = ttk.Label(
                        map_frame,
                        text="Click image to open for viewing/printing",
                        foreground="gray"
                    )
                    instruction.pack(pady=2)
                
                except Exception as e:
                    print(f"Error loading map image: {e}")
            
            # Add other info
            if "floor" in info:
                floor = ttk.Label(card, text=info["floor"])
                floor.pack(pady=2)
                
            if "wing" in info:
                wing = ttk.Label(card, text=info["wing"])
                wing.pack(pady=2)
                
            if "key_landmarks" in info:
                landmarks = ttk.Label(card, text="Key Landmarks:")
                landmarks.pack(pady=2)
                for landmark in info["key_landmarks"]:
                    lm = ttk.Label(card, text=f"• {landmark}")
                    lm.pack(pady=1)
                    
            # Add directions info if available
            if "steps" in info:
                steps = ttk.Label(card, text="Directions:")
                steps.pack(pady=2)
                for step in info["steps"]:
                    s = ttk.Label(card, text=f"• {step}", wraplength=330)
                    s.pack(pady=1)
                    
        # Add separator
        ttk.Separator(self.scrollable_frame).pack(fill="x", padx=10, pady=10)
        
    def add_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Add multiple action results to the window.
        
        :param results: List of action results
        """
        for result in results:
            self.add_result(result)
            
    def clear(self) -> None:
        """Clear all results from the window."""
        if self.scrollable_frame:
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
        self.images.clear()
        
    def show(self) -> None:
        """Show the window."""
        try:
            self.is_visible = True
            self._update_window_position()
            self.window.deiconify()
            self.window.lift()
        except (tk.TclError, AttributeError):
            # If window was destroyed, recreate it
            self._create_window()
            self.is_visible = True
            self._update_window_position()
            self.window.deiconify()
            self.window.lift()
        
    def hide(self) -> None:
        """Hide the window."""
        if self.window:
            try:
                self.is_visible = False
                self.window.withdraw()
            except tk.TclError:
                pass 

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Handle mouse wheel scrolling."""
        if event.num == 4 or event.delta > 0:  # Scroll up
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:  # Scroll down
            self.canvas.yview_scroll(1, "units") 