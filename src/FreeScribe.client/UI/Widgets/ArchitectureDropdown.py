import tkinter as tk
from tkinter import ttk

class ArchitectureDropdown:
    def __init__(self, parent, default_value, row=0, column=0):
        """
        Initializes the ArchitectureDropdown widget.

        Args:
            parent (tk.Widget): The parent widget where this component will be placed.
            default_value (str): the default to select
            row (int): The row position in the grid layout.
            column (int): The column position in the grid layout.
        """
        self.parent = parent
        self.default_value = default_value
        self.row = row
        self.column = column

        # Create widgets
        self.create_widgets()

    def create_widgets(self):
        """Creates and places the widgets for architecture selection."""
        # Label
        tk.Label(self.parent, text="Local Architecture").grid(
            row=self.row, column=self.column, padx=0, pady=5, sticky="w"
        )

        # Dropdown options
        architecture_options = ["CPU", "CUDA (Nvidia GPU)"]
        self.architecture_dropdown = ttk.Combobox(
            self.parent, values=architecture_options, width=15, state="readonly"
        )

        # Set default value from settings
        default_architecture = self.default_value
        if default_architecture in architecture_options:
            self.architecture_dropdown.current(architecture_options.index(default_architecture))
        else:
            self.architecture_dropdown.current(0)  # Default to the first option if not found

        # Place the dropdown in the grid
        self.architecture_dropdown.grid(
            row=self.row, column=self.column + 1, padx=0, pady=5, sticky="w"
        )

    def get_selected_architecture(self):
        """Returns the currently selected architecture."""
        return self.architecture_dropdown.get()

    def get(self):
        """Returns the currently selected architecture."""
        return self.get_selected_architecture()