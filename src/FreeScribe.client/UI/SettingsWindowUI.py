"""
SettingsWindowUI Module

This module provides a user interface for managing application settings.
It includes a class `SettingsWindowUI` that handles the creation and management
of a settings window using Tkinter.

This software is released under the AGPL-3.0 license
Copyright (c) 2023-2024 Braedon Hendy

Further updates and packaging added in 2024 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform". 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students - Software Developer Alex Simko, Pemba Sherpa (F24), and Naitik Patel.

Classes:
    SettingsWindowUI: Manages the settings window UI.
"""

import json
import logging
import tkinter as tk
from tkinter import ttk , messagebox
import threading
from pathlib import Path
import UI.Helpers
from Model import Model, ModelManager
from services.whisper_hallucination_cleaner import load_hallucination_cleaner_model
from utils.file_utils import get_file_path, get_resource_path
from utils.utils import get_application_version
from UI.MarkdownWindow import MarkdownWindow
from UI.SettingsWindow import SettingsWindow
from UI.SettingsConstant import SettingsKeys, Architectures, FeatureToggle
from UI.Widgets.PopupBox import PopupBox
import utils.log_config
from utils.log_config import logger
from constants.whisper_languages import WHISPER_LANGUAGE_CODES

import utils.whisper.Constants
from utils.whisper.WhisperModel import unload_stt_model

LONG_ENTRY_WIDTH = 30
SHORT_ENTRY_WIDTH = 20

logger = logging.getLogger(__name__)

class SettingsWindowUI:
    """
    Manages the settings window UI.

    This class creates and manages a settings window using Tkinter. It includes
    methods to open the settings window, create various settings frames, and
    handle user interactions such as saving settings.

    Attributes:
        settings (ApplicationSettings): The settings object containing application settings.
        window (tk.Toplevel): The main settings window.
        main_frame (tk.Frame): The main frame containing the notebook.
        notebook (ttk.Notebook): The notebook widget containing different settings tabs.
        general_frame (ttk.Frame): The frame for general settings.
        advanced_frame (ttk.Frame): The frame for advanced settings.
        docker_settings_frame (ttk.Frame): The frame for Docker settings.
        basic_settings_frame (tk.Frame): The scrollable frame for basic settings.
        advanced_settings_frame (tk.Frame): The scrollable frame for advanced settings.
    """

    def __init__(self, settings, main_window, root):
        """
        Initializes the SettingsWindowUI.

        Args:
            settings (ApplicationSettings): The settings object containing application settings.
        """
        self.settings = settings
        self.main_window = main_window
        self.root = root
        self.settings_window = None
        self.main_frame = None
        self.notebook = None
        self.basic_frame = None
        self.advanced_frame = None
        self.docker_settings_frame = None
        self.basic_settings_frame = None
        self.advanced_settings_frame = None
        self.display_notes_warning = True
        self.developer_frame = None
        self.widgets = {}
        

    def open_settings_window(self):
        """
        Opens the settings window.

        This method initializes and displays the settings window, including
        the notebook with tabs for basic, advanced, and Docker settings.
        """
        self.settings_window = tk.Toplevel()
        self.settings_window.title("Settings")
        if utils.system.is_windows():
            self.settings_window.geometry("775x400")  # Set initial window size
            self.settings_window.minsize(775, 400)    # Set minimum window size
        else:
            self.settings_window.geometry("1050x500")
            self.settings_window.minsize(1050, 500)

        self.settings_window.resizable(True, True)
        self.settings_window.grab_set()
        UI.Helpers.set_window_icon(self.settings_window)

        self._display_center_to_parent()

        self.main_frame = tk.Frame(self.settings_window)
        self.main_frame.pack(expand=True, fill='both')

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(expand=True, fill='both')

        self.general_settings_frame = ttk.Frame(self.notebook)
        self.llm_settings_frame = ttk.Frame(self.notebook)
        self.whisper_settings_frame = ttk.Frame(self.notebook)
        self.advanced_frame = ttk.Frame(self.notebook)
        self.docker_settings_frame = ttk.Frame(self.notebook)

        # Create container frame that will hold the scrollable frame
        self.developer_container = ttk.Frame(self.notebook)
        self.developer_frame = self.add_scrollbar_to_frame(self.developer_container)

        self.notebook.add(self.general_settings_frame, text="General Settings")
        self.notebook.add(self.whisper_settings_frame, text="Speech-to-Text Settings (Whisper)")
        self.notebook.add(self.llm_settings_frame, text="AI Settings (LLM)")
        self.notebook.add(self.advanced_frame, text="Advanced Settings")

        self.settings_window.protocol("WM_DELETE_WINDOW", self.close_window)

        self.advanced_settings_frame = self.add_scrollbar_to_frame(self.advanced_frame)

        # self.create_basic_settings()
        self._create_general_settings()
        self.create_llm_settings()
        self.create_whisper_settings()
        self.create_advanced_settings()
        self.create_developer_settings()

        if FeatureToggle.DOCKER_SETTINGS_TAB is True:
            self.notebook.add(self.docker_settings_frame, text="Docker Settings")
            self.create_docker_settings()
        
        self.create_buttons()

        # "Dev" settings tab for developer mode
        # Create the menu then disable it so the ui elements have access
        self.settings_window.bind("<Control-slash>", self._disable_developer_mode)
        self._disable_developer_mode(None)

        # set the focus to this window
        self.notebook.select(self.general_settings_frame)
        self.settings_window.focus_set()


    def _enable_developer_mode(self, event):      
        """
        add a developer tab to the notebook
        """
        if self.developer_container not in self.notebook.tabs():
            self.notebook.add(self.developer_container, text="Developer Settings")
        self.settings_window.unbind("<Control-slash>")
        self.settings_window.bind("<Control-slash>", self._disable_developer_mode)
        # select the developer tab automatically
        self.notebook.select(self.developer_container)

    def _disable_developer_mode(self, event):
        """
        remove the developer tab from the notebook
        """
        if self.developer_container in self.notebook.tabs():
            self.notebook.forget(self.developer_container)

        self.settings_window.unbind("<Control-slash>")
        self.settings_window.bind("<Control-slash>", self._enable_developer_mode)

    def create_developer_settings(self):
        """
        Creates the Developer settings UI elements.

        This method creates and places UI elements for Developer settings.
        """
        row = 1
        
        #warning headers
        row = self._create_section_header(
            text="⚠️ Developer Settings - Do Not Modify", 
            text_colour="red", 
            frame=self.developer_frame, 
            row=row)
        row = self._create_section_header(
            text="If you have accidentally accessed this menu please do not touch any of the settings below.", 
            row=row, 
            text_colour="red", 
            frame=self.developer_frame) 

        left_frame = ttk.Frame(self.developer_frame)
        left_frame.grid(row=row, column=0, padx=10, pady=5, sticky="nw")
        right_frame = ttk.Frame(self.developer_frame)
        right_frame.grid(row=row, column=1, padx=10, pady=5, sticky="nw")
        
        row += 1

        # load all settings from the developer settings        
        left_row, right_row = self.create_editable_settings_col(left_frame, right_frame, 0, 0, self.settings.developer_settings)
        
        if FeatureToggle.PRE_PROCESSING is True:
            self.preprocess_text, label_row, text_row, row = self._create_text_area(
                self.developer_frame, "Pre-Processing", self.settings.editable_settings["Pre-Processing"], row
            )

        row += 1

        # Intial prompt text field
        self.initial_prompt, label_row1, text_row1, row = self._create_text_area(
            self.developer_frame, "Whisper Initial Prompt", self.settings.editable_settings[SettingsKeys.WHISPER_INITIAL_PROMPT.value], row
        )

        # Explanation for Pre convo instruction
        initial_prompt_explanation = (
            "This is the initial Whisper prompt:\n\n"
            "• Guides how Whisper interprets and processes audio input\n"
            "• Defines transcription or translation format requirements\n"
            "• Can help whisper identify new vocabulary\n\n"
            "⚠️ Modify with caution as it influences the transcription/translation accuracy and quality"
        )

        tk.Label(
            self.developer_frame,
            text=initial_prompt_explanation,
            justify="left",
            font=("Arial", 9),
            fg="#272927"
        ).grid(row=text_row1, column=1, padx=(10, 0), pady=5, sticky="nw")
        
    def _display_center_to_parent(self):
        # Get parent window dimensions and position
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()

        # Calculate the position for the settings window
        settings_width = 775
        settings_height = 400
        center_x = parent_x + (parent_width - settings_width) // 2
        center_y = parent_y + (parent_height - settings_height) // 2

        # Apply the calculated position to the settings window
        self.settings_window.geometry(f"{settings_width}x{settings_height}+{center_x}+{center_y}")

    def add_scrollbar_to_frame(self, frame):
        """
        Adds a scrollbar to a given frame.

        Args:
            frame (tk.Frame): The frame to which the scrollbar will be added.

        Returns:
            tk.Frame: The scrollable frame.
        """
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.settings_window.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        return scrollable_frame

    def create_whisper_settings(self):
        """
        Creates the Whisper settings UI elements in a two-column layout.
        Settings alternate between left and right columns for even distribution.
        """

        left_frame = tk.Frame(self.whisper_settings_frame)
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        right_frame = tk.Frame(self.whisper_settings_frame)
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

        self.whisper_settings_frame.columnconfigure(0, weight=1)
        self.whisper_settings_frame.columnconfigure(1, weight=1)

        left_frame.columnconfigure(0, weight=3)  # Give weight to the label column
        left_frame.columnconfigure(1, weight=9)  # Give more weight to the dropdown column
        right_frame.columnconfigure(0, weight=3)  # Give weight to the label column
        right_frame.columnconfigure(1, weight=9)  # Give more weight to the dropdown column

        left_row = 0
        right_row = 0

        # Create the SettingsKeys.LOCAL_WHISPER button to handle custom behavior
        tk.Label(left_frame, text=f"{SettingsKeys.LOCAL_WHISPER.value}").grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        value = tk.IntVar(value=(self.settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]))
        self.local_whisper_checkbox = tk.Checkbutton(left_frame, variable=value, command=self.toggle_remote_whisper_settings)
        self.local_whisper_checkbox.grid(row=left_row, column=1, padx=0, pady=5, sticky="w")
        self.settings.editable_settings_entries[SettingsKeys.LOCAL_WHISPER.value] = value

        left_row += 1

        left_row, right_row = self.create_editable_settings_col(left_frame, right_frame, left_row, right_row, self.settings.whisper_settings)
        # create the whisper model dropdown slection
        tk.Label(left_frame, text=SettingsKeys.WHISPER_MODEL.value).grid(row=3, column=0, padx=0, pady=5, sticky="w")
        whisper_models_drop_down_options = utils.whisper.Constants.WhisperModels.get_all_labels()
        self.whisper_models_drop_down = ttk.Combobox(left_frame, values=whisper_models_drop_down_options, width=SHORT_ENTRY_WIDTH)
        self.whisper_models_drop_down.grid(row=3, column=1, padx=0, pady=5, sticky="w")

        try:
            # Try to set the whisper model dropdown to the current model
            self.whisper_models_drop_down.current(whisper_models_drop_down_options.index(self.settings.editable_settings[SettingsKeys.WHISPER_MODEL.value]))
        except ValueError:
            # If not in list then just force set text
            self.whisper_models_drop_down.set(self.settings.editable_settings[SettingsKeys.WHISPER_MODEL.value])

        self.settings.editable_settings_entries[SettingsKeys.WHISPER_MODEL.value] = self.whisper_models_drop_down

        # create the whisper model dropdown slection
        right_row += 1
        # Whisper Architecture Dropdown
        self.whisper_architecture_label = tk.Label(left_frame, text=SettingsKeys.WHISPER_ARCHITECTURE.value)
        self.whisper_architecture_label.grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        whisper_architecture_options = self.settings.get_available_architectures()
        self.whisper_architecture_dropdown = ttk.Combobox(left_frame, values=whisper_architecture_options, state="readonly")
        if self.settings.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value] in whisper_architecture_options:
            self.whisper_architecture_dropdown.current(whisper_architecture_options.index(self.settings.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value]))
        else:
            # Default cpu
            self.whisper_architecture_dropdown.set(SettingsWindow.DEFAULT_WHISPER_ARCHITECTURE)
        
        self.whisper_architecture_dropdown.grid(row=left_row, column=1, padx=0, pady=5, sticky="ew")
        self.settings.editable_settings_entries[SettingsKeys.WHISPER_ARCHITECTURE.value] = self.whisper_architecture_dropdown

        # remove architecture dropdown if architecture only has one option
        if len(whisper_architecture_options) == 1:
            self.whisper_architecture_label.grid_forget()
            self.whisper_architecture_dropdown.grid_forget()

        left_row += 1

        # set the state of the whisper settings based on the SettingsKeys.LOCAL_WHISPER.value checkbox once all widgets are created
        self.toggle_remote_whisper_settings()

    def toggle_remote_whisper_settings(self):
        current_state = self.settings.editable_settings_entries[SettingsKeys.LOCAL_WHISPER.value].get()
        
        for setting in self.settings.whisper_settings:
            if setting in [SettingsKeys.WHISPER_REAL_TIME.value, "BlankSpace"]:
                continue
            
            state = "normal" if current_state == 0 else "disabled"
            self.widgets[setting].config(state=state)
        
        # set the local option to disabled on switch to remote
        inverted_state = "disabled" if current_state == 0 else "normal"
        self.whisper_models_drop_down.config(state=inverted_state)
        self.whisper_architecture_dropdown.config(state=inverted_state)


    def create_llm_settings(self):
        """
        Creates the LLM settings UI elements in a two-column layout.
        Settings alternate between left and right columns for even distribution.
        """
        # Create left and right frames for the two columns
        left_frame = tk.Frame(self.llm_settings_frame)
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        right_frame = tk.Frame(self.llm_settings_frame)
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

        self.llm_settings_frame.columnconfigure(0, weight=1)
        self.llm_settings_frame.columnconfigure(1, weight=1)

        left_frame.columnconfigure(0, weight=3)  # Give weight to the label column
        left_frame.columnconfigure(1, weight=9)  # Give more weight to the dropdown column

        right_frame.columnconfigure(0, weight=3)  # Give weight to the label column
        right_frame.columnconfigure(1, weight=9)  # Give more weight to the dropdown column

        left_row = 0
        right_row = 0

        # Use local llm button with custom handler
        tk.Label(left_frame, text=SettingsKeys.LOCAL_LLM.value).grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        value = tk.IntVar(value=(self.settings.editable_settings[SettingsKeys.LOCAL_LLM.value]))
        self.local_llm_checkbox = tk.Checkbutton(left_frame, variable=value, command=self.toggle_remote_llm_settings)
        self.local_llm_checkbox.grid(row=left_row, column=1, padx=0, pady=5, sticky="w")
        self.settings.editable_settings_entries[SettingsKeys.LOCAL_LLM.value] = value

        left_row += 1

        #6. GPU OR CPU SELECTION (Right Column)
        self.local_architecture_label = tk.Label(left_frame, text=SettingsKeys.LLM_ARCHITECTURE.value)
        self.local_architecture_label.grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        architecture_options = self.settings.get_available_architectures()
        self.architecture_dropdown = ttk.Combobox(left_frame, values=architecture_options, state="readonly")
        if self.settings.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value] in architecture_options:
            self.architecture_dropdown.current(architecture_options.index(self.settings.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value]))
        else:
            # Default cpu
            self.architecture_dropdown.set(Architectures.CPU.label)

        self.architecture_dropdown.grid(row=left_row, column=1, padx=0, pady=5, sticky="ew")


        # hide architecture dropdown if architecture only has one option
        if len(architecture_options) == 1:
            self.local_architecture_label.grid_forget()
            self.architecture_dropdown.grid_forget()


        left_row += 1

        # 5. Models (Left Column)
        tk.Label(left_frame, text=SettingsKeys.LOCAL_LLM_MODEL.value).grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        models_drop_down_options = []
        models_drop_down_options = self._get_local_model_options()
        self.models_drop_down = ttk.Combobox(left_frame, values=models_drop_down_options, state="readonly")
        self.models_drop_down.grid(row=left_row, column=1, padx=0, pady=5, sticky="ew")
        self.models_drop_down.bind('<<ComboboxSelected>>', self.on_model_selection_change)
        # Create custom model entry (initially hidden) - removed fixed width and made it expandable
        self.custom_model_entry = tk.Entry(left_frame)
        self.custom_model_entry.insert(0, self.settings.editable_settings[SettingsKeys.LOCAL_LLM_MODEL.value])
        
        # Set current model selection
        current_model = self.settings.editable_settings[SettingsKeys.LOCAL_LLM_MODEL.value]
        if current_model in models_drop_down_options:
            self.models_drop_down.current(models_drop_down_options.index(current_model))
        else:
            # If current model is not in the list, show custom entry
            self.models_drop_down.set("Custom")
            self._show_custom_model_entry(left_row)
        
        # Start background thread to update with remote models if needed
        thread = threading.Thread(target=self.settings.update_models_dropdown, args=(self.models_drop_down,))
        thread.start()

        refresh_button = ttk.Button(left_frame, text="↻", 
                                command=self._refresh_models,
                                width=4)
        refresh_button.grid(row=left_row, column=2, padx=0, pady=5, sticky="w")

        left_row += 1

        right_frame, right_row = self.create_editable_settings(right_frame, self.settings.llm_settings, padx=0, pady=0)

        # 2. OpenAI API Key (Right Column)
        # Then modify your existing code
        tk.Label(right_frame, text=SettingsKeys.LLM_SERVER_API_KEY.value).grid(row=right_row, column=0, padx=0, pady=5, sticky="w")
        self.openai_api_key_entry = tk.Entry(right_frame)  # Remove fixed width
        self.openai_api_key_entry.insert(0, self.settings.OPENAI_API_KEY)
        self.openai_api_key_entry.grid(row=right_row, column=1, columnspan=2, padx=0, pady=5, sticky="ew")  # Changed to "ew
        
        right_row += 1

        #################################################################
        #                                                               #
        #               API STYLE SELECTION                             #
        #   THIS SECTION IS COMENTED OUT FOR FUTURE RELEASE AND REVIEW. #
        #   THE ONLY API STYLE SUPPORTED FOR NOW IS OPENAI.             #
        #   THE KOBOLD API STYLE HAS BEEN REMOVED FOR SIMPLIFICATION    #
        #                                                               #
        #################################################################
        # # 3. API Style (Left Column)
        # tk.Label(right_frame, text="API Style:").grid(row=right_row, column=0, padx=0, pady=5, sticky="w")
        # api_options = ["OpenAI", "KoboldCpp"]
        # self.api_dropdown = ttk.Combobox(right_frame, values=api_options, width=15, state="readonly")
        # self.api_dropdown.current(api_options.index(self.settings.API_STYLE))
        # self.api_dropdown.grid(row=right_row, column=1, columnspan=2, padx=0, pady=5, sticky="w")
        # right_row += 1

        # set the state of the llm settings based on the local llm checkbox once all widgets are created
        self.settings_opened = True
        self.toggle_remote_llm_settings()
 
    def toggle_remote_llm_settings(self):
        current_state = self.settings.editable_settings_entries[SettingsKeys.LOCAL_LLM.value].get()
        
        state = "normal" if current_state == 0 else "disabled"


        # toggle all manual settings based on the local llm checkbox
        self.openai_api_key_entry.config(state=state)
        # self.api_dropdown.config(state=state)

        for setting in self.settings.llm_settings:
            if setting == "BlankSpace":
                continue
            
            self.widgets[setting].config(state=state)

        inverted_state = "disabled" if current_state == 0 else "normal"
        self.architecture_dropdown.config(state=inverted_state)
        
        #flag used for determining if window was just opened so we dont spam the API.
        if not self.settings_opened:
            threading.Thread(target=self.settings.update_models_dropdown, args=(self.models_drop_down,self.settings.editable_settings_entries[SettingsKeys.LLM_ENDPOINT.value].get(),)).start()
        else:
            self.settings_opened = False
            
        self.on_model_selection_change(None)

    def on_model_selection_change(self, event):
        """
        Handle model selection change in the dropdown.
        Show/hide custom entry field based on selection.
        """
        if hasattr(self, 'models_drop_down'):
            selected_value = self.models_drop_down.get()
            
            model_row = None
            for child in self.models_drop_down.master.grid_slaves():
                if child == self.models_drop_down:
                    model_row = int(child.grid_info()["row"])
                    break
            
            if model_row is not None:
                if selected_value == "Custom":
                    self._show_custom_model_entry(model_row)
                else:
                    self._hide_custom_model_entry()

    def _show_custom_model_entry(self, row):
        """
        Show the custom model entry field with auto-scaling width.
        """
        # Hide the dropdown and show the custom entry
        self.models_drop_down.grid_forget()
        
        # Grid the custom entry with sticky="ew" to make it expand horizontally
        self.custom_model_entry.grid(row=row, column=1, padx=0, pady=5, sticky="ew")
        
        # Update the settings entry reference
        self.settings.editable_settings_entries[SettingsKeys.LOCAL_LLM_MODEL.value] = self.custom_model_entry

    def _hide_custom_model_entry(self):
        """
        Hide the custom model entry field and show the dropdown.
        """
        # Hide the custom entry and show the dropdown
        self.custom_model_entry.grid_forget()
        
        model_row = None
        for child in self.models_drop_down.master.grid_slaves():
            if child == self.custom_model_entry:
                model_row = int(child.grid_info()["row"])
                break
        
        # Re-grid the dropdown
        if model_row is not None:
            self.models_drop_down.grid(row=model_row, column=1, padx=0, pady=5, sticky="ew")
        else:
            self.models_drop_down.grid(row=2, column=1, padx=0, pady=5, sticky="ew")
            logger.warning("Could not find model row to re-grid the dropdown. Defaulting to row 2.")
        
        # Update the settings entry reference back to dropdown
        self.settings.editable_settings_entries[SettingsKeys.LOCAL_LLM_MODEL.value] = self.models_drop_down

    def get_selected_model(self):
        """Returns the selected model, either from dropdown or custom entry"""
        if self.models_drop_down.get() in ["Custom", "Select a Model"]:
            return self.custom_model_entry.get()
        return self.models_drop_down.get()

    def _get_local_model_options(self):
        root = Path.cwd() / "models"
        exts = ["*.gguf", "*.safetensors", "*.bin"]
        options = sorted({
            f"./models/{p.relative_to(root)}"
            for ext in exts
            for p in root.rglob(ext)
        }) if root.exists() else []

        if not options:
            options = ["No models found"]

        options.append("Custom")
        return options

    def create_editable_settings_col(self, left_frame, right_frame, left_row, right_row, settings_set):
        """
        Creates editable settings in two columns.

        This method splits the settings evenly between two columns and creates the
        corresponding UI elements in the left and right frames.

        :param left_frame: The frame for the left column.
        :param right_frame: The frame for the right column.
        :param left_row: The starting row for the left column.
        :param right_row: The starting row for the right column.
        :param settings_set: The set of settings to be displayed.
        :return: The updated row indices for the left and right columns.
        """
        mid_point = (len(settings_set) + 1) // 2  # Round up for odd numbers

        # Process left column
        left_row = self._process_column(left_frame, settings_set[:mid_point], left_row)

        # Process right column
        right_row = self._process_column(right_frame, settings_set[mid_point:], right_row)

        return left_row, right_row
    
    def _process_column(self, frame, settings, start_row):
        """
        Processes a column of settings.

        This helper method creates the UI elements for a column of settings.

        :param frame: The frame for the column.
        :param settings: The settings to be displayed in the column.
        :param start_row: The starting row for the column.
        :return: The updated row index for the column.
        """
        row = start_row
        for setting_name in settings:

            if setting_name == "BlankSpace":
                row += 1
                continue

            boolean_settings = [key for key, type_value in self.settings.setting_types.items() 
                            if type_value == bool]
            if setting_name in boolean_settings:
                self.widgets[setting_name] = self._create_checkbox(frame, setting_name, setting_name, row)
            else:
                self.widgets[setting_name] = self._create_entry(frame, setting_name, setting_name, row)
            row += 1
        return row

    def create_advanced_settings(self):
        """Creates the advanced settings UI elements with a structured layout."""

        def create_settings_columns(settings, row):
            left_frame = ttk.Frame(self.advanced_settings_frame)
            right_frame = ttk.Frame(self.advanced_settings_frame)
            left_frame.grid(row=row, column=0, padx=10, pady=5, sticky="nw")
            right_frame.grid(row=row, column=1, padx=10, pady=5, sticky="nw")
            self.create_editable_settings_col(left_frame, right_frame, 0, 0, settings)
            return row + 1

        row = self._create_section_header("⚠️ Advanced Settings (For Advanced Users Only)", 0, text_colour="red", frame=self.advanced_settings_frame)
        
        # General Settings
        if len(self.settings.adv_general_settings) > 0:
            row = self._create_section_header("General Settings", row, text_colour="black", frame=self.advanced_settings_frame)
            row = create_settings_columns(self.settings.adv_general_settings, row)

        if FeatureToggle.INTENT_ACTION:
            # Google Maps Integration
            row = self._create_section_header("Google Maps Integration", row, frame=self.advanced_settings_frame, text_colour="black")
            maps_frame = ttk.LabelFrame(self.advanced_settings_frame, text="API Configuration")
            maps_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
            
            ttk.Label(maps_frame, text="API Key:").grid(row=0, column=0, padx=5, pady=5)
            maps_key_entry = ttk.Entry(maps_frame, show="*")  # Hide API key
            maps_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            maps_key_entry.insert(0, self.settings.editable_settings[SettingsKeys.GOOGLE_MAPS_API_KEY.value])
            
            def toggle_key_visibility():
                current = maps_key_entry.cget("show")
                maps_key_entry.configure(show="" if current == "*" else "*")
            
            ttk.Button(maps_frame, text="👁", width=3, command=toggle_key_visibility).grid(row=0, column=2, padx=5, pady=5)
            
            maps_frame.grid_columnconfigure(1, weight=1)  # Make the entry expand horizontally
            self.widgets[SettingsKeys.GOOGLE_MAPS_API_KEY.value] = maps_key_entry
            row += 1

        # Whisper Settings
        row = self._create_section_header("Whisper Settings", row, text_colour="black", frame=self.advanced_settings_frame)
        left_frame = ttk.Frame(self.advanced_settings_frame)
        left_frame.grid(row=row, column=0, padx=10, pady=5, sticky="nw")
        right_frame = ttk.Frame(self.advanced_settings_frame)
        right_frame.grid(row=row, column=1, padx=10, pady=5, sticky="nw")

        # Create all whisper settings except language code (we'll handle that specially)
        whisper_settings = [s for s in self.settings.adv_whisper_settings if s != SettingsKeys.WHISPER_LANGUAGE_CODE.value]
        self.create_editable_settings_col(left_frame, right_frame, 0, 0, whisper_settings)

        # Whisper Language Code Dropdown
        tk.Label(left_frame, text=SettingsKeys.WHISPER_LANGUAGE_CODE.value).grid(row=len(whisper_settings), column=0, padx=0,
pady=5, sticky="w")
        self.whisper_language_dropdown = ttk.Combobox(left_frame, values=WHISPER_LANGUAGE_CODES, state="readonly")
        current_lang = self.settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value]
        if current_lang in WHISPER_LANGUAGE_CODES:
            self.whisper_language_dropdown.current(WHISPER_LANGUAGE_CODES.index(current_lang))
        else:
            self.whisper_language_dropdown.set(current_lang)  # Fallback to current value if not in list
        self.whisper_language_dropdown.grid(row=len(whisper_settings), column=1, padx=0, pady=5, sticky="ew")
        self.settings.editable_settings_entries[SettingsKeys.WHISPER_LANGUAGE_CODE.value] = self.whisper_language_dropdown
        
        row += 1

        # AI Settings
        row = self._create_section_header("AI Settings", row, text_colour="black", frame=self.advanced_settings_frame)
        row = create_settings_columns(self.settings.adv_ai_settings, row)
        
        if FeatureToggle.POST_PROCESSING is True:
            self.postprocess_text, _ = self.__create_processing_section(
                self.advanced_settings_frame,
                "Post-Processing (Experimental. Use with caution.)",
                "Use Post-Processing", 
                self.settings.editable_settings["Post-Processing"],
                row
            )

        # add watchers for save encrypted files
        self.settings.editable_settings_entries[SettingsKeys.STORE_RECORDINGS_LOCALLY.value].trace_add(
            "write",
            lambda *args: self.__display_encrypted_phi_warning(SettingsKeys.STORE_RECORDINGS_LOCALLY.value)
        )

        self.settings.editable_settings_entries[SettingsKeys.ENABLE_FILE_LOGGER.value].trace_add(
            "write",
            lambda *args: self.__display_encrypted_phi_warning(SettingsKeys.ENABLE_FILE_LOGGER.value)
        )

        self.settings.editable_settings_entries[SettingsKeys.STORE_NOTES_LOCALLY.value].trace_add(
            "write",
            lambda *args: self.toggle_store_notes_locally()
        )

    def toggle_store_notes_locally(self):
        """
        Handle toggling the Store Notes Locally checkbox.
        Shows a warning popup on the main window when attempting to disable this setting.
        """
        # Convert IntVar to boolean
        current_value = bool(self.settings.editable_settings_entries[SettingsKeys.STORE_NOTES_LOCALLY.value].get())
        
        # If the checkbox was unchecked (value is now False), show the warning popup
        if not current_value and self.display_notes_warning:
            # Create a popup warning dialog on the main window
            confirm = messagebox.askokcancel(
                "Warning",
                "Disabling Store Notes Locally (Encrypted) will delete the existing saved notes",
                icon="warning",
                parent=self.root  # Use the main window as the parent
            )
            
            if not confirm:
                # User clicked Cancel, revert the checkbox to checked
                self.settings.editable_settings_entries[SettingsKeys.STORE_NOTES_LOCALLY.value].set(1)
        else:
            self.display_notes_warning = False  # Reset the flag to show the warning next time
            self.__display_encrypted_phi_warning(SettingsKeys.STORE_NOTES_LOCALLY.value)

        self.display_notes_warning = True  # Reset the flag to show the warning next time


    def __display_encrypted_phi_warning(self, setting_name):
        """
        Displays a warning message for encrypted PHI files.
        """
        # Check if the setting is enabled (1)
        if not self.settings.editable_settings_entries[setting_name].get():
            return # No need to show the warning if the setting is disabled

        warning_message = (
            "⚠️ Warning: Encrypted PHI Data Storage",
            "You are about to save encrypted Protected Health Information (PHI) to disk.",
            "While this data is securely encrypted,  you should still exercise care in how you manage these files."
            "Please ensure the file is stored in a secure location and access is appropriately restricted.",
            "Do you still wish to proceed?",
        )
        result = tk.messagebox.askyesno(
            "Warning",
            "\n".join(warning_message),
            icon="warning",
        )

        if not result:
            print("User chose not to proceed with saving encrypted PHI data.")
            self.settings.editable_settings_entries[setting_name].set(0)  # Disable the checkbox
            self.widgets[setting_name].config(variable=self.settings.editable_settings_entries[setting_name])  # Disable the checkbox

    def __create_processing_section(self, frame, label_text, setting_key, text_content, row):
        button_frame = tk.Frame(frame, width=800)
        button_frame.grid(row=row, column=0, padx=10, pady=0, sticky="nw")
        self._create_checkbox(button_frame, f"Use {label_text}", setting_key, 0)
        row += 1
        
        text_area, label_row, text_row, column_row = self._create_text_area(frame, label_text, text_content, row)
        return text_area, row

    def create_docker_settings(self):
        """
        Creates the Docker settings UI elements.

        This method creates and places UI elements for Docker settings.
        """
        self.create_editable_settings(self.docker_settings_frame, self.settings.docker_settings)

    def create_editable_settings(self, frame, settings_set, start_row=0, padx=10, pady=5):
        """
        Creates editable settings UI elements.

        Args:
            frame (tk.Frame): The frame in which to create the settings.
            settings_set (list): The list of settings to create UI elements for.
            start_row (int): The starting row for placing the settings.
        """
        
        # Configure the parent frame to expand
        frame.columnconfigure(0, weight=1)
        
        # Create inner frame that will expand to fill parent
        i_frame = ttk.Frame(frame)
        i_frame.grid(row=0, column=0, columnspan=2,padx=padx, pady=pady, sticky="ew")
        
        # Configure the inner frame's columns
        i_frame.columnconfigure(0, weight=1)  # Give weight to the label column
        i_frame.columnconfigure(1, weight=3)  # Give more weight to the dropdown column
        
        row = self._process_column(i_frame, settings_set, start_row)
        return i_frame, row

    def create_buttons(self):
        """
        Creates the buttons for the settings window.

        This method creates and places buttons for saving settings, resetting to default,
        and closing the settings window.
        """
        footer_frame = tk.Frame(self.main_frame,bg="lightgray", height=30)
        footer_frame.pack(side="bottom", fill="x")

        # Place the "Help" button on the left
        tk.Button(footer_frame, text="Help", width=10, command=self.create_help_window).pack(side="left", padx=2, pady=5)

        # Place the label in the center
        version = get_application_version()
        tk.Label(footer_frame, text=f"FreeScribe Client {version}",bg="lightgray",fg="black").pack(side="left", expand=True, padx=2, pady=5)

        # Create a frame for the right-side elements
        right_frame = tk.Frame(footer_frame,bg="lightgray")
        right_frame.pack(side="right")

        # Pack all other buttons into the right frame
        tk.Button(right_frame, text="Close", width=10, command=self.close_window).pack(side="right", padx=2, pady=5)
        tk.Button(right_frame, text="Default", width=10, command=self.reset_to_default).pack(side="right", padx=2, pady=5)
        tk.Button(right_frame, text="Save", width=10, command=self.save_settings).pack(side="right", padx=2, pady=5)

    def create_help_window(self):
        """
        Creates a help window for the settings.

        Uses our markdown window class to display a markdown with help
        """
        MarkdownWindow(self.settings_window, "Help", get_file_path('markdown','help','settings.md'))

    def save_settings(self, close_window=True):
        """
        Saves the settings entered by the user.

        This method retrieves the values from the UI elements and calls the
        `save_settings` method of the `settings` object to save the settings.
        """
        # delay actual unload/reload till settings are actually saved
        local_model_unload_flag, local_model_reload_flag = self.settings.load_or_unload_model(
            self.settings.editable_settings[SettingsKeys.LOCAL_LLM_MODEL.value],
            self.get_selected_model(),
            self.settings.editable_settings[SettingsKeys.LOCAL_LLM.value],
            self.settings.editable_settings_entries[SettingsKeys.LOCAL_LLM.value].get(),
            self.settings.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value],
            self.architecture_dropdown.get(),
            self.settings.editable_settings[SettingsKeys.LOCAL_LLM_CONTEXT_WINDOW.value],
            self.settings.editable_settings_entries[SettingsKeys.LOCAL_LLM_CONTEXT_WINDOW.value].get(),
            self.settings.editable_settings_entries[SettingsKeys.USE_LOW_MEM_MODE.value].get(),
            self.settings.editable_settings[SettingsKeys.USE_LOW_MEM_MODE.value]
        )
        
        self.__initialize_file_logger()
        self.__initialize_notes_history()

        if self.get_selected_model() not in ["Loading models...", "Failed to load models"]:
            self.settings.editable_settings[SettingsKeys.LOCAL_LLM_MODEL.value] = self.get_selected_model()

        # delay update, or the update thread might be reading old settings value
        update_whisper_model_flag = self.settings.update_whisper_model()

        load_hallucination_cleaner_model(self.main_window.root, self.settings)

        if FeatureToggle.PRE_PROCESSING is True:
            self.settings.editable_settings["Pre-Processing"] = self.preprocess_text.get("1.0", "end-1c") # end-1c removes the trailing newline
        
        if FeatureToggle.POST_PROCESSING is True:
            self.settings.editable_settings["Post-Processing"] = self.postprocess_text.get("1.0", "end-1c") # end-1c removes the trailing newline

        # save architecture
        self.settings.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value] = self.architecture_dropdown.get()

        # save the intial prompt
        self.settings.editable_settings[SettingsKeys.WHISPER_INITIAL_PROMPT.value] = self.initial_prompt.get("1.0", "end-1c") # end-1c removes the trailing newline

        if FeatureToggle.INTENT_ACTION:
            # Save Google Maps API key
            self.settings.editable_settings[SettingsKeys.GOOGLE_MAPS_API_KEY.value] = self.widgets[SettingsKeys.GOOGLE_MAPS_API_KEY.value].get()

        
        if not self.settings.save_settings(
                self.openai_api_key_entry.get(),
                self.settings_window,
                # self.api_dropdown.get(),
                self.settings.editable_settings["Silence cut-off"], # Save the old one for whisper audio cutoff, will be removed in future, left in incase we go back to old cut off
                # self.cutoff_slider.threshold / 32768, # old threshold 
            ):
            return
        # send load event after the settings are saved
        if update_whisper_model_flag:
            self.main_window.root.event_generate("<<LoadSttModel>>")
        # unload whisper model if switched to remote
        if not self.settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]:
            self.main_window.root.event_generate("<<UnloadSttModel>>")
        # unload / reload model after the settings are saved
        if local_model_unload_flag:
            logger.debug("unloading ai model")
            ModelManager.unload_model()
        if local_model_reload_flag:
            logger.debug("reloading ai model")
            ModelManager.start_model_threaded(self.settings, self.main_window.root)

        #update the notes and Ui
        self.main_window.root.event_generate("<<ProcessDataTab>>")

        # check if we should unload the model
        # unload models if low mem is now on
        if self.settings.editable_settings_entries[SettingsKeys.USE_LOW_MEM_MODE.value].get():
            unload_stt_model()

        if self.settings.editable_settings["Use Docker Status Bar"] and self.main_window.docker_status_bar is None:
            self.main_window.create_docker_status_bar()
        elif not self.settings.editable_settings["Use Docker Status Bar"] and self.main_window.docker_status_bar is not None:
            self.main_window.destroy_docker_status_bar()
        
        self.main_window.root.event_generate("<<TranscribeOnlyModeChanged>>")

        if close_window:
            self.close_window()

    def _refresh_models(self):
        """
        Refreshes the local model options by rescanning the models folder
        and reverts to dropdown view. Only works when local LLM is enabled.
        """
        # Only allow refresh when local LLM is enabled
        if self.settings.editable_settings_entries[SettingsKeys.LOCAL_LLM.value].get():
            logger.info("Refreshing local model options...")
            
            # Rescan local models from file system
            new_model_options = self._get_local_model_options()
        
            self._hide_custom_model_entry()
             
            # Set dropdown to first available model or "No models found"
            if len(new_model_options) > 1:  # More than just "Custom"
                self.models_drop_down.set(new_model_options[0])
            else:
                self.models_drop_down.set("No models found")

            # Update the dropdown with new options
            self.models_drop_down['values'] = new_model_options
            
        else:
            self.save_settings(False)
            threading.Thread(target=self.settings.update_models_dropdown, args=(self.models_drop_down,)).start()
            self.on_model_selection_change(None)

    def __initialize_notes_history(self):
        """
        Initializes the notes history setting based on the current editable settings.
        """
        old_value = self.settings.editable_settings[SettingsKeys.STORE_NOTES_LOCALLY.value]
        new_value = self.settings.editable_settings_entries[SettingsKeys.STORE_NOTES_LOCALLY.value].get()

        # check the checkbox again the current setting
        if old_value == new_value:
            logger.info("Notes history setting unchanged.")
            return
        
        if new_value == 1:
            logger.info("Notes history enabled.")
            self.root.event_generate("<<EnableNoteHistory>>")
        else:
            logger.info("Notes history disabled.")
            self.root.event_generate("<<DisableNoteHistory>>")

    def __initialize_file_logger(self):
        # if un changed, do nothing
        logger.info("Checking file logging setting...")
        if self.settings.editable_settings_entries[SettingsKeys.ENABLE_FILE_LOGGER.value].get() == self.settings.editable_settings[SettingsKeys.ENABLE_FILE_LOGGER.value]:
            logger.info("File logging setting unchanged.")
            return

        if self.settings.editable_settings_entries[SettingsKeys.ENABLE_FILE_LOGGER.value].get() == 1:
            utils.log_config.add_file_handler(utils.log_config.logger, utils.log_config.AESEncryptedFormatter())
            logger.info("File logging enabled.")
        else:
            utils.log_config.remove_file_handler(utils.log_config.logger)
            logger.info("File logging disabled.")

    def reset_to_default(self, show_confirmation=True):
        """
        Resets the settings to their default values.

        This method calls the `clear_settings_file` method of the `settings` object
        to reset the settings to their default values.
        """

        if show_confirmation:
            popup = PopupBox(parent=self.settings_window, 
                message="Are you sure you want to reset all settings to default?", 
                title="Reset to Default", 
                button_text_2="Cancel",
                button_text_1="Reset to Default", 
                button_text_3="Keep Network Settings")
            if popup.response == "button_2":
                return
            elif popup.response == "button_3":
                self.settings.clear_settings_file(self.settings_window, keep_network_settings=True)
                return
            elif popup.response == "button_1":
                self.settings.clear_settings_file(self.settings_window)

    def _create_general_settings(self):
        """
        Creates the general settings UI elements.

        This method creates and places UI elements for general settings.
        """
        # Create frames for a two-column layout
        left_frame = ttk.Frame(self.general_settings_frame)
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")

        right_frame = ttk.Frame(self.general_settings_frame)
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nw")

        left_row = 0
        right_row = 0

        # Create the rest of the general settings
        left_row, right_row = self.create_editable_settings_col(left_frame, right_frame, left_row, right_row, self.settings.general_settings)

        # Add a note at the bottom of the general settings frame
        note_text = (
        "NOTE: To protect personal health information (PHI), we recommend using a local network.\n"
        "The 'Show Scrub PHI' feature is only applicable for local LLMs and private networks.\n"
        "For internet-facing endpoints, this feature will always be enabled, regardless of the 'Show Scrub PHI' setting."
    )

        # Create a frame to hold the note labels
        note_frame = tk.Frame(self.general_settings_frame)
        note_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        font_size = 12 if utils.system.is_windows() else 14
        # Add the red * label
        star_label = tk.Label(note_frame, text="*", fg="red", font=("Arial", font_size, "bold"))
        star_label.grid(row=0, column=0, sticky="w")

        font_size = 9 if utils.system.is_windows() else 12
        # Add the rest of the text in black (bold)
        note_label = tk.Label(
            note_frame,
            text=note_text,
            font=("Arial", font_size, "bold"),  # Set font to bold
            wraplength=400,
            justify="left"
        )
        note_label.grid(row=0, column=1, sticky="w")
    def _create_checkbox(self, frame, label, setting_name, row_idx, setting_key=None):
        """
        Creates a checkbox in the given frame.

        This method creates a label and a checkbox in the given frame for editing.

        Args:
            frame (tk.Frame): The frame in which to create the checkbox.
            label (str): The label to display next to the checkbox.
            setting_name (str): The name of the setting to edit.
            row_idx (int): The row index at which to place the checkbox.
        """
        tk.Label(frame, text=label).grid(row=row_idx, column=0, padx=0, pady=5, sticky="w")
        # Convert to bool to ensure proper type
        current_value = bool(self.settings.editable_settings[setting_name])
        value = tk.BooleanVar(value=current_value)
        checkbox = tk.Checkbutton(frame, variable=value)
        checkbox.grid(row=row_idx, column=1, padx=0, pady=5, sticky="w")
        self.settings.editable_settings_entries[setting_name] = value
        return checkbox

    def _create_entry(self, frame, label, setting_name, row_idx):
        """
        Creates an entry field in the given frame.

        This method creates a label and an entry field in the given frame for editing.
        
        Args:
            frame (tk.Frame): The frame in which to create the entry field.
            label (str): The label to display next to the entry field.
            setting_name (str): The name of the setting to edit.
            row_idx (int): The row index at which to place the entry field.
        """
        tk.Label(frame, text=label).grid(row=row_idx, column=0, padx=0, pady=5, sticky="w")
        value = self.settings.editable_settings[setting_name]

        # Convert the value to the appropriate type using the helper method
        if hasattr(self.settings, 'convert_setting_value'):
            value = self.settings.convert_setting_value(setting_name, value)
        
        entry = tk.Entry(frame)
        entry.insert(0, str(value))
        entry.grid(row=row_idx, column=1, padx=0, pady=5, sticky="ew")
        self.settings.editable_settings_entries[setting_name] = entry
        return entry

    def _create_section_header(self, text, row, frame, text_colour="black"):
        """
        Creates a section header label in the advanced settings frame.
        
        Args:
            text (str): Text to display in the header
            row (int): Grid row position to place the header
            text_colour (str): Color of header text (default "black")
            
        Returns:
            int: Next available grid row number
        """
        ttk.Label(
            frame, 
            text=text,
            font=("TkDefaultFont", 10, "bold"),
            foreground=text_colour
        ).grid(row=row, column=0, columnspan=2, padx=10, 
            pady=(5 if text.startswith("⚠️") else 0, 10 if text.startswith("⚠️") else 0), 
            sticky="w")
        return row + 1

    def _create_text_area(self, frame, label_text, text_content, row):
        """
        Creates a labeled text area widget in the advanced settings frame.
        
        Args:
            label_text (str): Label text to display above text area
            text_content (str): Initial text to populate the text area
            row (int): Starting grid row position
            
        Returns:
            tuple: (Text widget object, label_row, text_row, next_row)
        """
        label_row = row
        tk.Label(frame, text=label_text).grid(
            row=label_row, column=0, padx=10, pady=5, sticky="w")
        
        text_row = row + 1
        text_area = tk.Text(frame, height=10, width=50)
        text_area.insert(tk.END, text_content)
        text_area.grid(row=text_row, column=0, padx=10, pady=5, sticky="w")
        
        return text_area, label_row, text_row, row + 2

    def __focus_and_lift_root_window(self):
        """
        Focuses and lifts the root window above other windows.
        """
        # Lift up to the top of all windows open
        self.root.lift()
        # Focus on the root window again incase lost
        self.root.focus_force()

    def add_scrollbar_to_frame(self, frame):
        """
        Adds a scrollbar to a given frame.

        Args:
            frame (tk.Frame): The frame to which the scrollbar will be added.

        Returns:
            tk.Frame: The scrollable frame.
        """
        # Create scrollable frame components
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if canvas.winfo_exists():  # Check if canvas still exists
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                return "break"

        # Bind mousewheel only when mouse is over the canvas
        canvas.bind('<Enter>', lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all("<MouseWheel>"))

        return scrollable_frame      

    def close_window(self):
        """
        Cleans up the settings window.

        This method destroys the settings window and clears the settings entries.
        """
        self.settings_window.unbind_all("<MouseWheel>") # Unbind mouse wheel event causing errors
        self.settings_window.unbind_all("<Configure>") # Unbind the configure event causing errors
        
        if hasattr(self, "cutoff_slider"):
            if self.cutoff_slider is not None:
                self.cutoff_slider.destroy()

        self.settings_window.destroy()

        self.__focus_and_lift_root_window()
