import logging
import tkinter as tk
import tkinter.messagebox as messagebox
from utils.log_config import logger


class TimestampListbox(tk.Listbox):
    """A custom Listbox widget that allows editing of timestamp entries.

    This widget extends tk.Listbox to provide right-click editing functionality
    for timestamp entries and maintains synchronization with a response history.

    :param args: Variable length argument list passed to tk.Listbox
    :param kwargs: Arbitrary keyword arguments, with special handling for:
        - response_history: List of tuples containing (timestamp, user_message, response)
    :type args: tuple
    :type kwargs: dict
    """
    def __init__(self, *args, **kwargs):
        """Initialize the TimestampListbox widget.

        :param args: Variable length argument list passed to tk.Listbox
        :param kwargs: Arbitrary keyword arguments, with special handling for:
            - response_history: List of tuples containing (timestamp, user_message, response)
        :type args: tuple
        :type kwargs: dict
        """
        response_history = kwargs.pop('response_history')
        super().__init__(*args, **kwargs)
        self.response_history = response_history
        self.edit_entry = None
        self.edit_index = None

        # Setup right-click menu
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Rename", command=self.start_edit)
        self.bind("<Button-3>", self.on_right_click)

    def on_right_click(self, event):
        """Handle right-click events to show context menu.

        :param event: The mouse event containing position information
        :type event: tk.Event
        """
        index = self.nearest(event.y)
        self.selection_clear(0, tk.END)
        self.selection_set(index)
        self.activate(index)
        self.event_generate('<<ListboxSelect>>')
        self.menu.post(event.x_root, event.y_root)

    def start_edit(self):
        """Start editing the selected timestamp entry.

        Creates an Entry widget over the selected list item and sets focus to it.
        """
        selection = self.curselection()
        if not selection:
            return

        self.edit_index = selection[0]
        current_text = self.get(self.edit_index)
        self.see(self.edit_index)

        bbox = self.bbox(self.edit_index)
        if not bbox:
            return

        self.edit_entry = tk.Entry(self)
        self.edit_entry.insert(0, current_text)
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.place(x=bbox[0], y=bbox[1], width=self.winfo_width(), height=bbox[3])
        self.edit_entry.focus_set()

        self.edit_entry.bind("<Return>", lambda e: self.confirm_edit())
        self.edit_entry.bind("<Escape>", lambda e: self.cancel_edit())
        self.edit_entry.bind("<FocusOut>", lambda e: self.confirm_edit())

    def confirm_edit(self):
        """Confirm and save the edited timestamp.

        Updates both the Listbox entry and the corresponding response history.

        :raises tk.TclError: If there are widget-related issues
        :raises ValueError: If the timestamp format is invalid
        :raises Exception: For any other unexpected errors (logged and re-raised)
        """
        try:
            if self.edit_entry and self.edit_index is not None:
                new_text = self.edit_entry.get()
                self.delete(self.edit_index)
                self.insert(self.edit_index, new_text)

                # Update the corresponding response history
                if self.edit_index < len(self.response_history):
                    timestamp, user_message, response = self.response_history[self.edit_index]
                    self.response_history[self.edit_index] = (new_text, user_message, response)

                self.edit_entry.destroy()
                self.edit_entry = None
                self.edit_index = None
        except tk.TclError as e:
            # Handle Tkinter-specific errors (e.g., widget-related issues)
            messagebox.showerror("UI Error", f"Failed to update timestamp: {str(e)}")
        except ValueError as e:
            # Handle validation errors
            messagebox.showwarning("Invalid Input", f"Invalid timestamp format: {str(e)}")
        except Exception as e:
            # Log unexpected errors and re-raise them
            logger.error(f"Critical error while confirming timestamp edit: {str(e)}")
            raise  # Re-raise unexpected exceptions to prevent silent failures

    def cancel_edit(self):
        """Cancel the editing operation.

        Destroys the edit Entry widget and resets editing state.

        :raises tk.TclError: If there are widget-related issues
        :raises ValueError: If the timestamp format is invalid
        :raises Exception: For any other unexpected errors (logged and re-raised)
        """
        try:
            if self.edit_entry and self.edit_index is not None:
                self.edit_entry.destroy()
                self.edit_entry = None
                self.edit_index = None
        except tk.TclError as e:
            # Handle Tkinter-specific errors (e.g., widget-related issues)
            messagebox.showerror("UI Error", f"Failed to update timestamp: {str(e)}")
        except ValueError as e:
            # Handle validation errors
            messagebox.showwarning("Invalid Input", f"Invalid timestamp format: {str(e)}")
        except Exception as e:
            # Log unexpected errors and re-raise them
            logger.error(f"Critical error while confirming timestamp edit: {str(e)}")
            raise  # Re-raise unexpected exceptions to prevent silent failures
