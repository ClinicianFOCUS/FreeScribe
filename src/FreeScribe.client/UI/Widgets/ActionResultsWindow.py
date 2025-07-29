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

CANVAS_LAYOUT_THRESHOLD = 1  # Minimum width for canvas layout to apply

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
        self.min_width = 400
        self.min_height = 300
        
        self._create_window()
        
        # Bind to parent window events
        self.parent.bind("<Configure>", self._on_parent_moved)
        
        # Initialize label styles
        self._init_label_styles()
        
    def _init_label_styles(self):
        """
        Initialize custom label styles for card labels.
        Should be called once, e.g., in __init__.
        """
        style = ttk.Style()
        # Default label style for cards
        style.configure("CardLabel.TLabel", foreground="black")
        # Completed card label style
        style.configure("CardLabel.Complete.TLabel", foreground="gray50")
        
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
        self.window.minsize(self.min_width, self.min_height)
        self.window.resizable(True, True)
        
        # Remove window decorations but keep resize border
        self.window.overrideredirect(False)
        
        # Set window attributes to keep it below other windows
        self.window.attributes('-topmost', False)
        
        # Configure custom styles for completed cards
        style = ttk.Style()
        try:
            style.configure("CompletedCard.TFrame", background="gray90")
        except tk.TclError:
            # Fallback if style configuration fails
            pass
        
        # Create main container frame
        main_container = ttk.Frame(self.window)
        main_container.pack(fill="both", expand=True)
        
        # Create title bar with close button
        title_bar = ttk.Frame(main_container)
        title_bar.pack(fill="x", padx=0, pady=0)
        
        # Add title
        title_label = ttk.Label(title_bar, text="Action Results", style="CardTitle.TLabel")
        title_label.pack(side="left", padx=10, pady=5)
        
        # Add close button
        close_button = ttk.Label(title_bar, text="✕", cursor="hand2")
        close_button.pack(side="right", padx=10, pady=5)
        close_button.bind("<Button-1>", lambda e: self.hide())
        
        # Add separator below title bar
        ttk.Separator(main_container, orient="horizontal").pack(fill="x")
        
        # Create main content area
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill="both", expand=True)
        
        # Create scrollable frame
        self.canvas = tk.Canvas(content_frame)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling
        def configure_scroll_region(event=None):
            if hasattr(self, 'canvas_window') and self.canvas_window:  # Guard against undefined canvas_window
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                # Make the scrollable frame fill the canvas width
                canvas_width = self.canvas.winfo_width()
                if canvas_width > CANVAS_LAYOUT_THRESHOLD:  # Ensure canvas has been drawn
                    self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        

        self.scrollable_frame.bind("<Configure>", configure_scroll_region)
        
        # Create the window in the canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind canvas resize to update frame width
        self.canvas.bind("<Configure>", configure_scroll_region)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add Clear All button at the bottom
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill="x", side="bottom", pady=5)
        
        clear_all_button = ttk.Button(
            bottom_frame,
            text="Clear All",
            style="Danger.TButton",
            cursor="hand2",
            command=self.clear
        )
        clear_all_button.pack(pady=5)
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Initially hide the window
        self.window.withdraw()
        
        # Update window position
        self._update_window_position()
        
        # Bind mouse wheel events
        self._bind_mouse_wheel_events()
        
        # Configure canvas to resize with window
        self.window.bind("<Configure>", self._on_window_configure)
        
    def _on_window_configure(self, event: tk.Event) -> None:
        """Handle window resize events."""
        if event.widget == self.window:
            # Update canvas width to match window width
            self.canvas.configure(width=event.width - 20)  # Account for scrollbar and padding
            
    def _bind_mouse_wheel_events(self) -> None:
        """Bind mouse wheel events to the canvas."""
        def _bind_to_mousewheel(event):
            if event.widget == self.canvas:
                return
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            self.canvas.bind_all("<Button-4>", self._on_mousewheel)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel)
            
        def _unbind_from_mousewheel(event):
            if event.widget == self.canvas:
                return
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")
        
        # Bind mouse wheel to canvas permanently
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        
        # Bind enter/leave events to scrollable frame
        self.scrollable_frame.bind("<Enter>", _bind_to_mousewheel)
        self.scrollable_frame.bind("<Leave>", _unbind_from_mousewheel)
        
    def _update_window_position(self) -> None:
        """Update the window position to stay on the right side of parent."""
        if not self.window or not self.is_visible:
            return
            
        try:
            # Get parent window position and size
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            
            # Calculate position for results window - add 15px gap
            window_x = parent_x + parent_width + 15
            window_y = parent_y
            
            # Get current window size
            window_width = self.window.winfo_width()
            window_height = self.window.winfo_height()
            
            # Set window position while preserving size
            self.window.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")
            
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
        
        # Add header with delete button
        header = ttk.Frame(card)
        header.pack(fill="x", padx=5, pady=5)
        
        # Left side: icon and title
        left_frame = ttk.Frame(header)
        left_frame.pack(side="left", fill="x", expand=True)
        
        icon = ttk.Label(left_frame, text=result["ui"]["icon"])
        icon.pack(side="left", padx=5)
        
        title = ttk.Label(left_frame, text=result["display_name"], style="CardLabel.TLabel")
        title.pack(side="left", padx=5)
        
        # Right side: delete button
        delete_button = ttk.Label(
            header,
            text="🗑️",
            cursor="hand2",
            foreground="red"
        )
        delete_button.pack(side="right", padx=5)
        delete_button.bind("<Button-1>", lambda e: self._delete_card(card))
        
        # Add message
        message = ttk.Label(
            card, 
            text=result["message"], 
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
                    logger.exception(f"Error loading map image: {e}")
                    
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
                    logger.exception(f"Error loading map image: {e}")
            
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
                    
        # Add footer with action button and completion checkbox
        footer = ttk.Frame(card)
        footer.pack(fill="x", padx=5, pady=(10, 5))
        
        # Add completed checkbox in bottom right - pack directly to footer
        completed_var = tk.BooleanVar()
        
        completed_checkbox = ttk.Checkbutton(
            footer,
            variable=completed_var,
            cursor="hand2",
            command=lambda: self._toggle_card_completed(card, completed_var.get(), result)
        )
        completed_checkbox.pack(side="right")
        
        complete_label = ttk.Label(footer, text="Complete:")
        complete_label.pack(side="right", padx=(0, 5))
        
        # Get data members with defaults
        has_action = result["data"].get("has_action", False)
        auto_complete = result["data"].get("auto_complete", True)
              
        # Left side: action button (always show)
        if has_action:
            if auto_complete:
                action_button = ttk.Button(
                    footer,
                    text="Auto Completing Action",
                    state="disabled",
                    cursor="arrow"
                )
                # Schedule auto-completion to run after UI is updated
                self.window.after(0, lambda: self._complete_action(result, action_button, completed_checkbox))
            else:
                action_button = ttk.Button(
                    footer,
                    text="Complete Action",
                    cursor="hand2",
                    command=lambda: self._complete_action(result, action_button, completed_checkbox)
                )
        else:
            # No action available - show disabled button
            action_button = ttk.Button(
                footer,
                text="No Action",
                state="disabled",
                cursor="arrow"
            )
        action_button.pack(side="left")

                # If auto_complete is True and has_action is True, trigger the action automatically
        if has_action and auto_complete:
            # Schedule auto-completion to run after UI is updated
            self.window.after(0, lambda: self._complete_action(result, action_button, completed_checkbox))

        # Add separator
        ttk.Separator(self.scrollable_frame).pack(fill="x", padx=10, pady=10)
        
        # Update the scroll region and scroll to the bottom
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(1.0)  # Scroll to bottom
        
    def add_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Add multiple action results to the window.
        
        :param results: List of action results
        """
        for result in results:
            self.add_result(result)
            
    def _complete_action(self, result: Dict[str, Any], button: ttk.Button, checkbox: ttk.Checkbutton) -> None:
        """
        Handle the complete action button click.

        :param result: The action result data
        :param button: The button widget to update
        :param checkbox: The checkbox widget to update
        """
        try:
            # Get the action instance from the result data
            action = result["data"].get("action")
            if action:
                # Call the action's complete_action method
                success = action()
                if success:
                    logger.info(f"Action completed successfully for: {result.get('display_name', 'Unknown')}")
                else:
                    logger.warning(f"Action completion failed for: {result.get('display_name', 'Unknown')}")
            else:
                # Fallback to generic logging if no action instance available
                logger.info(f"Completing action for: {result.get('display_name', 'Unknown')}")

            # Update the button text and disable it
            if result["data"].get("auto_complete", False):
                button.config(text="Action Automatically Completed", state="disabled")
            else:
                button.config(text="Action Manually Completed", state="disabled")

            # Check the checkbox
            checkbox.invoke()  # Simulate checking the checkbox

        except Exception as e:
            logger.exception(f"Error completing action: {str(e)}")
            
    def _toggle_card_completed(self, card: ttk.Frame, is_completed: bool, result: Dict[str, Any]) -> None:
        """
        Toggle the completed state of a card, greying it out when completed.

        :param card: The card frame to toggle
        :param is_completed: Whether the card is marked as completed
        :param result: The result data associated with the card
        """
        try:
            # Update the result data with the completed state
            result['completed'] = is_completed

            # Configure card appearance based on completion state
            if is_completed:
                # Grey out the card
                card.configure(style="CompletedCard.TFrame")
                # Make all text elements in the card appear greyed out
                self._set_card_text_color(card, "gray50")
            else:
                # Restore normal appearance
                card.configure(style="Card.TFrame")
                # Restore normal text colors
                self._set_card_text_color(card, None)
                
        except (AttributeError, tk.TclError) as e:
            logger.error(f"Error toggling card completion: {str(e)}")
        except Exception as e:
            logger.critical(f"Unexpected error toggling card completion: {str(e)}")
            raise
    
    def _set_card_text_color(self, widget, color) -> None:
        """
        Recursively set label style for all label widgets in a card.

        :param widget: The widget to process
        :param color: The color to set (None for default)
        """
        try:
            # Process current widget if it's a label
            if isinstance(widget, ttk.Label):
                if color == "gray50":
                    widget.configure(style="CardLabel.Complete.TLabel")
                else:
                    # Reset to default style
                    widget.configure(style="CardLabel.TLabel")

            # Recursively process children
            for child in widget.winfo_children():
                self._set_card_text_color(child, color)

        except Exception as e:
            logger.debug(f"Error setting text color: {str(e)}")
            
    def _delete_card(self, card: ttk.Frame) -> None:
        """
        Delete a specific card from the window.
        
        :param card: The card frame to delete
        """
        try:
            # Get all children of scrollable_frame
            children = self.scrollable_frame.winfo_children()
            # Find the index of current card
            card_index = children.index(card)
            
            # If there's a next widget and it's a separator, delete it
            if card_index + 1 < len(children) and isinstance(children[card_index + 1], ttk.Separator):
                children[card_index + 1].destroy()
            # If it's not the first card and the previous widget is a separator, delete the previous separator
            elif card_index > 0 and isinstance(children[card_index - 1], ttk.Separator):
                children[card_index - 1].destroy()
                
            # Destroy the card
            card.destroy()
            
            # Update the scroll region
            self.scrollable_frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        except Exception as e:
            logger.error(f"Error deleting card: {str(e)}")
            # If anything goes wrong, just try to destroy the card
            try:
                card.destroy()
            except:
                pass
        
    def clear(self) -> None:
        """Clear all results from the window."""
        if self.scrollable_frame:
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
        self.images.clear()
        
        # Update the scroll region
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def show(self) -> None:
        """Show the window."""
        try:
            self.is_visible = True
            self._update_window_position()
            self.window.deiconify()
            # Don't lift the window automatically
        except (tk.TclError, AttributeError):
            # If window was destroyed, recreate it
            self._create_window()
            self.is_visible = True
            self._update_window_position()
            self.window.deiconify()
            # Don't lift the window automatically
        
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