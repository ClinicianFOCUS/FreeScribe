import logging
import tkinter as tk


class TimestampListbox(tk.Listbox):
    def __init__(self, *args, **kwargs):
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
        index = self.nearest(event.y)
        self.selection_clear(0, tk.END)
        self.selection_set(index)
        self.activate(index)
        self.event_generate('<<ListboxSelect>>')
        self.menu.post(event.x_root, event.y_root)

    def start_edit(self):
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
        self.edit_entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        self.edit_entry.focus_set()

        self.edit_entry.bind("<Return>", lambda e: self.confirm_edit())
        self.edit_entry.bind("<Escape>", lambda e: self.cancel_edit())
        self.edit_entry.bind("<FocusOut>", lambda e: self.confirm_edit())

    def confirm_edit(self):
        """Confirm and save the edited timestamp"""
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
        except Exception as e:
            logging.exception(f"Error confirm edit {str(e)}")

    def cancel_edit(self):
        """Cancel the editing operation"""
        try:
            if self.edit_entry and self.edit_index is not None:
                self.edit_entry.destroy()
                self.edit_entry = None
                self.edit_index = None
        except Exception as e:
            logging.exception(f"Error canceling edit: {e}")
