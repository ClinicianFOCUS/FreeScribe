"""
NoteStyleSelector Module

This module provides a user interface for managing note style templates and prompts.
It includes classes for selecting, creating, editing, and deleting AI prompt templates
used for generating different types of clinical notes (SOAP notes, etc.).

This software is released under the AGPL-3.0 license
Copyright (c) 2023-2024 Braedon Hendy

Further updates and packaging added in 2024 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform". 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students - Software Developer Alex Simko, Pemba Sherpa (F24), and Naitik Patel.

Classes:
    StylePromptInfo: Data class for storing style prompt information.
    NoteStyleSelector: Main widget for selecting and managing note styles.
    StyleDialog: Dialog window for creating and editing style templates.
"""
import tkinter as tk
import UI.Helpers
from tkinter import ttk, simpledialog, messagebox
from dataclasses import dataclass
import json
import os
from utils.log_config import logger
from utils.file_utils import get_resource_path

@dataclass
class StylePromptInfo:
    """
    Data class for storing style prompt information.

    Attributes:
        style_name (str): The name of the style.
        pre_prompt (str): The prompt text that appears before the conversation.
        post_prompt (str): The prompt text that appears after the conversation.
    """
    style_name: str
    pre_prompt: str
    post_prompt: str

class NoteStyleSelector(tk.Frame):
    """
    A Tkinter frame widget for selecting and managing note styles.
    
    This class provides a dropdown selector for note styles along with
    edit and delete buttons. It manages style data persistence and
    provides static methods for accessing current style information.

    Attributes:
        current_style (str): The currently selected style name.
        style_data (dict): Dictionary containing style data with pre/post prompts.
        style_options (list): List of available style options for the dropdown.
        _styles_file (str): Path to the JSON file storing style data.
    """
    # Static class variables
    current_style = "SOAP Note - Default"
    # Store style data with pre/post prompts
    style_data = {}
    style_options = ["Add Prompt Template...", "No Note Generation", "SOAP Note - Default"]
    _styles_file = "note_styles.json"
    _styles_path = get_resource_path(_styles_file)
    
    @classmethod
    def _get_default_styles(cls):
        """
        Returns the default styles configuration.

        Returns:
            dict: Dictionary containing default style configurations with
                  pre_prompt and post_prompt for each style.
        """
        return {
            "No Note Generation": {
                "pre_prompt": "",
                "post_prompt": ""
            },
            "SOAP Note - Default": {
                "pre_prompt": "AI, please transform the following conversation into a concise SOAP note. Do not assume any medical data, vital signs, or lab values. Base the note strictly on the information provided in the conversation. Ensure that the SOAP note is structured appropriately with Subjective, Objective, Assessment, and Plan sections. Strictly extract facts from the conversation. Here's the conversation:",
                "post_prompt": "Remember, the Subjective section should reflect the patient's perspective and complaints as mentioned in the conversation. The Objective section should only include observable or measurable data from the conversation. The Assessment should be a summary of your understanding and potential diagnoses, considering the conversation's content. The Plan should outline the proposed management, strictly based on the dialogue provided. Do not add any information that did not occur and do not make assumptions. Strictly extract facts from the conversation."
            }
        }
    
    @classmethod
    def load_styles(cls):
        """
        Loads styles from disk and creates defaults if file doesn't exist.
        
        This method reads the styles JSON file, loads existing styles into
        class variables, and creates default styles if no file exists.
        Updates the style_options list with custom styles.

        Args:
            None

        Returns:
            None
        """
        try:
            if os.path.exists(cls._styles_path):
                with open(cls._styles_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cls.style_data = data.get('styles', {})
                    cls.current_style = data.get('current_style', "SOAP Note - Default")
            else:
                # Create default styles
                cls.style_data = cls._get_default_styles()
                cls.current_style = "SOAP Note - Default"
                cls.save_styles()
            
            # Update style_options list - only add custom styles that aren't already in the list
            custom_styles = [style for style in cls.style_data.keys() if style not in cls.style_options]
            cls.style_options = ["Add Prompt Template...", "No Note Generation", "SOAP Note - Default"] + custom_styles

        except Exception as e:
            logger.exception(f"Error loading styles: {e}")
            # Fallback to defaults
            cls.style_data = cls._get_default_styles()
            cls.current_style = "SOAP Note - Default"
            # Only add custom styles that aren't already in the list
            custom_styles = [style for style in cls.style_data.keys() if style not in cls.style_options]
            cls.style_options = ["Add Prompt Template...", "No Note Generation", "SOAP Note - Default"] + custom_styles

    @classmethod
    def save_styles(cls):
        """
        Saves current styles to disk.
        
        Writes the current style data and selected style to the JSON file.
        Handles encoding and error management during the save process.

        Args:
            None

        Returns:
            None
        """
        try:
            data = {
                'styles': cls.style_data,
                'current_style': cls.current_style
            }
            with open(cls._styles_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.exception(f"Error saving styles: {e}")
    
    def __init__(self, root=None, parent_frame=None):
        """
        Initializes the NoteStyleSelector widget.
        
        Loads styles if not already loaded and creates the widget UI.
        Sets up the frame with the specified parent and background.

        Args:
            root (tk.Tk, optional): The root window reference.
            parent_frame (tk.Frame, optional): The parent frame to contain this widget.

        Returns:
            None
        """
        # Load styles before initializing
        if not hasattr(NoteStyleSelector, '_styles_loaded'):
            NoteStyleSelector.load_styles()
            NoteStyleSelector._styles_loaded = True
            
        super().__init__(parent_frame, bg=parent_frame.cget("bg"))
        self.root = root
        self.parent_frame = parent_frame
        self.create_widgets()

    def create_widgets(self):
        """
        Creates and arranges the UI widgets for the note style selector.
        
        Sets up the combobox dropdown for style selection and the
        edit/delete buttons. Binds event handlers for user interactions.

        Args:
            None

        Returns:
            None
        """
        # Frame to hold dropdown and buttons horizontally
        self.style_var = tk.StringVar(value=NoteStyleSelector.current_style)

        self.style_combo = ttk.Combobox(self, textvariable=self.style_var, 
                                       values=NoteStyleSelector.style_options, state="readonly", width=35)
        self.style_combo.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        self.style_combo.bind("<<ComboboxSelected>>", self.on_style_change)

        self.edit_button = tk.Button(self, text="Edit", command=self.edit_style)
        self.edit_button.pack(side=tk.LEFT, padx=2)

        self.delete_button = tk.Button(self, text="Delete", command=self.delete_style)
        self.delete_button.pack(side=tk.LEFT, padx=2)

    @staticmethod
    def get_current_prompt_info() -> StylePromptInfo:
        """
        Gets the current style's prompt information.
        
        Returns a StylePromptInfo object containing the current style's
        name, pre-prompt, and post-prompt text.

        Args:
            None

        Returns:
            StylePromptInfo: Object containing current style information.
        """
        current_style = NoteStyleSelector.current_style
        if current_style in NoteStyleSelector.style_data:
            return StylePromptInfo(
                style_name=current_style,
                pre_prompt=NoteStyleSelector.style_data[current_style]['pre_prompt'],
                post_prompt=NoteStyleSelector.style_data[current_style]['post_prompt']
            )
        else:
            return StylePromptInfo(
                style_name=current_style,
                pre_prompt='',
                post_prompt=''
            )

    def on_style_change(self, event=None):
        """
        Handles style selection changes in the dropdown.
        
        When a user selects a different style, this method either opens
        the add style dialog (if "Add Prompt Template..." is selected)
        or updates the current style and saves the changes.

        Args:
            event (tk.Event, optional): The event object from the combobox selection.

        Returns:
            None
        """
        selected_value = self.style_var.get()
        if selected_value == "Add Prompt Template...":
            new_style_name = self.add_style()
            # Select the newly added style if it was created
            if new_style_name and new_style_name in NoteStyleSelector.style_options:
                self.style_var.set(new_style_name)
                NoteStyleSelector.current_style = new_style_name
                NoteStyleSelector.save_styles()
            elif len(NoteStyleSelector.style_options) > 1:
                # Reset to current style
                self.style_var.set(NoteStyleSelector.current_style)
        else:
            NoteStyleSelector.current_style = selected_value
            NoteStyleSelector.save_styles()

    def add_style(self):
        """
        Opens a dialog to add a new prompt template style.
        
        Creates a StyleDialog for entering new style information,
        adds the new style to the system if valid, and updates
        the dropdown and current selection.

        Args:
            None

        Returns:
            str or None: The name of the newly added style if successful, None otherwise.
        """
        # Create a custom dialog for style creation
        dialog = StyleDialog(self.root, "Add Prompt Template")
        if dialog.result:
            style_name, pre_prompt, post_prompt = dialog.result
            if style_name and style_name not in NoteStyleSelector.style_options:
                NoteStyleSelector.style_options.append(style_name)
                NoteStyleSelector.style_data[style_name] = {
                    'pre_prompt': pre_prompt,
                    'post_prompt': post_prompt
                }
                self.update_dropdown()
                # Return the new style name so it can be selected
                return style_name
        return None

    def edit_style(self):
        """
        Opens a dialog to edit or view the currently selected style.
        
        For default styles, opens in read-only view mode. For custom styles,
        allows editing of the style name and prompt content. Updates the
        system with any changes made.

        Args:
            None

        Returns:
            None
        """
        current_style = self.style_var.get()
        if current_style == "Add Prompt Template...":
            messagebox.showwarning("Edit Template", "Cannot edit 'Add Prompt Template...' option.")
            return
        
        # Get existing data if available
        existing_data = NoteStyleSelector.style_data.get(current_style, {'pre_prompt': '', 'post_prompt': ''})
        
        # Check if it's a protected style - allow viewing but not editing
        is_protected = (current_style in ["SOAP Note - Default", "No Note Generation"])

        dialog = StyleDialog(self.root, "View Template" if is_protected else "Edit Template",
                           initial_name=current_style,
                           initial_pre=existing_data['pre_prompt'],
                           initial_post=existing_data['post_prompt'],
                           read_only=is_protected,
                           is_edit=True)
        
        if dialog.result and not is_protected:
            new_name, pre_prompt, post_prompt = dialog.result
            if new_name and new_name != current_style and new_name not in NoteStyleSelector.style_options:
                # Replace the old style with the new one
                index = NoteStyleSelector.style_options.index(current_style)
                NoteStyleSelector.style_options[index] = new_name
                
                # Remove old data and add new
                if current_style in NoteStyleSelector.style_data:
                    del NoteStyleSelector.style_data[current_style]
                NoteStyleSelector.style_data[new_name] = {
                    'pre_prompt': pre_prompt,
                    'post_prompt': post_prompt
                }
                
                self.update_dropdown()
                self.style_var.set(new_name)
                NoteStyleSelector.current_style = new_name
                NoteStyleSelector.save_styles()
            elif new_name == current_style:
                # Just update the prompts
                NoteStyleSelector.style_data[current_style] = {
                    'pre_prompt': pre_prompt,
                    'post_prompt': post_prompt
                }
                NoteStyleSelector.save_styles()

    def delete_style(self):
        """
        Deletes the currently selected style after confirmation.
        
        Prevents deletion of protected styles ("Add Prompt Template...",
        "No Note Generation", and "SOAP Note - Default"). Shows confirmation 
        dialog before deletion and resets to default style after deletion.

        Args:
            None

        Returns:
            None
        """
        current_style = self.style_var.get()
        if current_style in ["Add Prompt Template...", "No Note Generation", "SOAP Note - Default"]:
            messagebox.showwarning("Delete Template", "Cannot delete 'Add Prompt Template...', 'No Note Generation', or 'SOAP Note - Default' template.")
            return

        if messagebox.askyesno("Delete Template", f"Are you sure you want to delete '{current_style}'?"):
            # Check if template exists in options before attempting removal
            if current_style in NoteStyleSelector.style_options:
                NoteStyleSelector.style_options.remove(current_style)
            if current_style in NoteStyleSelector.style_data:
                del NoteStyleSelector.style_data[current_style]
            self.update_dropdown()
            # Set to default after deletion
            self.style_var.set("SOAP Note - Default")
            NoteStyleSelector.current_style = "SOAP Note - Default"
            NoteStyleSelector.save_styles()

    def update_dropdown(self):
        """
        Updates the dropdown combobox with current style options.
        
        Refreshes the values displayed in the combobox to reflect
        any changes in the available styles.

        Args:
            None

        Returns:
            None
        """
        # Update the Combobox values
        self.style_combo['values'] = NoteStyleSelector.style_options

    def apply_style(self):
        """
        Applies the currently selected style and prints its information.
        
        Retrieves the current style's prompt information and displays
        it to the console. Used for testing and debugging purposes.

        Args:
            None

        Returns:
            None
        """
        selected_style = self.style_var.get()
        if selected_style != "Add Prompt Template...":
            prompt_info = NoteStyleSelector.get_current_prompt_info()
            logger.info(f"Selected Note Style: {prompt_info.style_name}")
            logger.debug(f"Pre Prompt: {prompt_info.pre_prompt}")
            logger.debug(f"Post Prompt: {prompt_info.post_prompt}")

class StyleDialog:
    """
    A dialog window for creating and editing note style templates.
    
    This class creates a modal dialog that allows users to input or modify
    style template information including name, pre-prompt, and post-prompt.
    Supports both editable and read-only modes.

    Attributes:
        result (tuple): Contains (name, pre_prompt, post_prompt) if dialog completed successfully.
        read_only (bool): Whether the dialog is in read-only mode.
        dialog (tk.Toplevel): The dialog window.
    """
    def __init__(self, parent, title, initial_name="", initial_pre="", initial_post="", read_only=False, is_edit=False):
        """
        Initializes the StyleDialog window.
        
        Creates and displays a modal dialog for editing style information.
        Sets up the UI components and waits for user interaction.

        Args:
            parent (tk.Widget): The parent window for this dialog.
            title (str): The title to display in the dialog window.
            initial_name (str, optional): Initial value for the style name field.
            initial_pre (str, optional): Initial value for the pre-prompt field.
            initial_post (str, optional): Initial value for the post-prompt field.
            read_only (bool, optional): Whether to display in read-only mode.

        Returns:
            None
        """
        self.result = None
        self.read_only = read_only
        self.warning_frame = None  # Will hold the error warning frame
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        # Slightly taller to accommodate warning
        self.dialog.geometry("900x650")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.focus_force()
        self.dialog.lift()
        
        # Make it stay on top
        self.dialog.attributes('-topmost', True)
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
             
        # Style name
        self.name_label = tk.Label(self.dialog, text="Template Name:")
        self.name_label.pack(pady=5)
        self.name_entry = tk.Entry(self.dialog, width=50, font=('Arial', 10))
        self.name_entry.pack(pady=5)
        self.name_entry.insert(0, initial_name)
        if self.read_only:
            self.name_entry.configure(state='disabled')
        
        # Pre prompt section with explanation
        tk.Label(self.dialog, text="Pre Prompt:").pack(pady=(15, 5))
        
        pre_frame = tk.Frame(self.dialog)
        pre_frame.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
        
        # Pre prompt text box
        self.pre_text = tk.Text(pre_frame, height=8, width=50, font=('Arial', 9))
        self.pre_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.pre_text.insert(tk.END, initial_pre)
        if self.read_only:
            self.pre_text.configure(state='disabled')
        
        # Pre prompt explanation
        pre_explanation = (
            "This is the FIRST part of the AI prompt structure:\n\n"
            "• Acts as the opening instruction to the AI\n"
            "• Sets up how to interpret the conversation\n"
            "• Defines SOAP note format requirements\n"
            "• Conversation will be inserted after this\n\n"
            "⚠️ Modify with caution as it affects AI output quality"
        )
        
        pre_explanation_label = tk.Label(pre_frame, text=pre_explanation, 
                                       justify=tk.LEFT, anchor='nw', 
                                       font=('Arial', 8), fg='gray',
                                       wraplength=215, width=35)
        pre_explanation_label.pack(side=tk.RIGHT, padx=(10, 0), fill=tk.Y)
        
        # Post prompt section with explanation
        tk.Label(self.dialog, text="Post Prompt:").pack(pady=(15, 5))
        
        post_frame = tk.Frame(self.dialog)
        post_frame.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
        
        # Post prompt text box
        self.post_text = tk.Text(post_frame, height=8, width=50, font=('Arial', 9))
        self.post_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.post_text.insert(tk.END, initial_post)
        if self.read_only:
            self.post_text.configure(state='disabled')
        
        # Post prompt explanation
        post_explanation = (
            "This is the LAST part of the AI prompt structure:\n\n"
            "• Added after the conversation text\n"
            "• Provides final formatting instructions\n"
            "• Ensures SOAP note completeness\n"
            "• Helps maintain consistency\n\n"
            "⚠️ Modify with caution as it affects AI output quality"
        )
        
        post_explanation_label = tk.Label(post_frame, text=post_explanation, 
                                        justify=tk.LEFT, anchor='nw', 
                                        font=('Arial', 8), fg='gray',
                                        wraplength=215, width=35)
        post_explanation_label.pack(side=tk.RIGHT, padx=(10, 0), fill=tk.Y)
        
        # Buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=20, fill=tk.X)
        
        # Center the buttons
        inner_frame = tk.Frame(button_frame)
        inner_frame.pack()
        
        # Only show OK button if not read-only, or disable it if read-only
        if self.read_only:
            ok_button = tk.Button(inner_frame, text="OK", command=lambda: self.ok_clicked(is_edit=is_edit), 
                                width=10, font=('Arial', 10), state='disabled')
            ok_button.pack(side=tk.LEFT, padx=10)
            tk.Button(inner_frame, text="Close", command=self.cancel_clicked, 
                     width=10, font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
        else:
            tk.Button(inner_frame, text="OK", command=lambda: self.ok_clicked(is_edit=is_edit), 
                     width=10, font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
            tk.Button(inner_frame, text="Cancel", command=self.cancel_clicked, 
                     width=10, font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
        
        # Focus on name entry (if not disabled)
        if not self.read_only:
            self.name_entry.focus_set()
            self.name_entry.select_range(0, tk.END)
        
        UI.Helpers.center_window_to_parent(self.dialog, parent)
        UI.Helpers.set_window_icon(self.dialog)

        # Add warning for read-only mode
        if self.read_only:
            self.show_error_warning("⚠️ Cannot edit default note template - View only mode")

        # Wait for dialog to close
        self.dialog.wait_window()
    
    def show_error_warning(self, message):
        """
        Shows an error warning frame at the top of the dialog.
        
        Args:
            message (str): The error message to display.
        """
        # Remove existing warning frame if present
        if self.warning_frame:
            self.warning_frame.destroy()
        
        # Create new warning frame
        self.warning_frame = tk.Frame(self.dialog, bg='#ffeeee', relief='raised', bd=2)
        self.warning_frame.pack(fill=tk.X, padx=10, pady=5, before=self.name_label)
        warning_label = tk.Label(self.warning_frame, 
                               text=message,
                               bg='#ffeeee', fg='#cc0000', font=('Arial', 10, 'bold'))
        warning_label.pack(pady=5)
    
    def hide_error_warning(self):
        """
        Hides the error warning frame if it exists.
        """
        if self.warning_frame:
            self.warning_frame.destroy()
            self.warning_frame = None
    
    def ok_clicked(self, is_edit=False):
        """
        Handles the OK button click event.
        
        Validates the input fields and stores the result if valid.
        Closes the dialog window after processing.

        Args:
            None

        Returns:
            None
        """
        if self.read_only:
            # Shouldn't be called in read-only mode, but just in case
            return  
            
        name = self.name_entry.get().strip()
        pre_prompt = self.pre_text.get("1.0", tk.END).strip()
        post_prompt = self.post_text.get("1.0", tk.END).strip()
        
        if not name:
            self.show_error_warning("⚠️ Template name cannot be empty - Please enter a title")
            self.name_entry.focus_set()
            return
        else:
            if not is_edit and name in NoteStyleSelector.style_options:
                self.show_error_warning(f"⚠️ Template '{name}' already exists - Please choose a different name")
                return
    
        # Hide any existing warning if validation passes
        self.hide_error_warning()
        
        if name:
            self.result = (name, pre_prompt, post_prompt)
        
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """
        Handles the Cancel/Close button click event.
        
        Closes the dialog window without saving any changes.

        Args:
            None

        Returns:
            None
        """
        self.dialog.destroy()

if __name__ == "__main__":
    # build a sample tkinter window to test the NoteStyleSelector

    root = tk.Tk()
    root.title("Note Template Selector Test")

    note_style_selector = NoteStyleSelector(root)
    note_style_selector.pack()

    root.mainloop()
