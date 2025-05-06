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

import logging
import tkinter as tk
from tkinter import ttk
import threading
from Model import Model, ModelManager
from services.whisper_hallucination_cleaner import load_hallucination_cleaner_model
from utils.file_utils import get_file_path, get_resource_path
from utils.utils import get_application_version
from UI.MarkdownWindow import MarkdownWindow
from UI.SettingsWindow import SettingsWindow
from UI.SettingsConstant import SettingsKeys, Architectures, FeatureToggle
from UI.Widgets.PopupBox import PopupBox
from utils.system_utils import get_system_memory, get_system_vram
from DataModels import WhisperModelEnum
import utils.log_config
from utils.log_config import logger
logger = logging.getLogger(__name__)

LONG_ENTRY_WIDTH = 30
SHORT_ENTRY_WIDTH = 20


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
        self.widgets = {}
        

    def open_settings_window(self):
        """
        Opens the settings window.

        This method initializes and displays the settings window, including
        the notebook with tabs for basic, advanced, and Docker settings.
        """
        self.settings_window = tk.Toplevel()
        self.settings_window.title("Settings")
        self.settings_window.geometry("775x400")  # Set initial window size
        self.settings_window.minsize(775, 400)    # Set minimum window size
        self.settings_window.resizable(True, True)
        self.settings_window.grab_set()
        self.settings_window.iconbitmap(get_file_path('assets','logo.ico'))

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

        self.notebook.add(self.general_settings_frame, text="General Settings")
        self.notebook.add(self.whisper_settings_frame, text="Speech-to-Text Settings (Whisper)")
        self.notebook.add(self.llm_settings_frame, text="AI Settings (LLM)")
        self.notebook.add(self.advanced_frame, text="Advanced Settings")

        self.settings_window.protocol("WM_DELETE_WINDOW", self.close_window)


        self.llm_settings_frame = self.add_scrollbar_to_frame(self.llm_settings_frame)
        self.whisper_settings_frame = self.add_scrollbar_to_frame(self.whisper_settings_frame)
        self.advanced_settings_frame = self.add_scrollbar_to_frame(self.advanced_frame)

        # self.create_basic_settings()
        self._create_general_settings()
        self.create_llm_settings()
        self.create_whisper_settings()
        self.create_advanced_settings()

        if FeatureToggle.DOCKER_SETTINGS_TAB is True:
            self.notebook.add(self.docker_settings_frame, text="Docker Settings")
            self.create_docker_settings()
        
        self.create_buttons()

        # "Dev" settings tab for developer mode
        # Create the menu then disable it so the ui elements have access
        self._enable_developer_mode(None)
        self._disable_developer_mode(None)
        self.developer_frame = ttk.Frame(self.notebook)
        self.create_developer_settings(self.developer_frame)

        self.settings_window.bind("<Control-slash>", self._enable_developer_mode)

        # set the focus to this window
        self.settings_window.focus_set()


    def _enable_developer_mode(self, event):      
        """
        add a developer tab to the notebook
        """
        self.notebook.add(self.developer_frame, text="Developer Settings")
        self.settings_window.unbind("<Control-slash>")
        self.settings_window.bind("<Control-slash>", self._disable_developer_mode)
        # select the developer tab automatically
        self.notebook.select(self.developer_frame)

    def _disable_developer_mode(self, event):
        """
        remove the developer tab from the notebook
        """
        self.notebook.hide(self.developer_frame)
        self.settings_window.unbind("<Control-slash>")
        self.settings_window.bind("<Control-slash>", self._enable_developer_mode)

    def create_developer_settings(self, frame):
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

        # load all settings from the developer settings        
        left_row, right_row = self.create_editable_settings_col(left_frame, right_frame, 0, 0, self.settings.developer_settings)

        # add custom handler for log file button, additional warning for PHI
        def _on_file_logger_click(*args):
            if self.settings.editable_settings_entries[SettingsKeys.ENABLE_FILE_LOGGER.value].get() == 1:
                # Give a disclaimer for potential PHI leak
                result = messagebox.askokcancel(
                    title="Warning",
                    message="Enabling file logging may expose sensitive information such as patient PHI. Use with caution. The log file can be located at:\n" + get_resource_path('freescribe.log'),
                    icon="warning"
                )

                # Check the result (True if OK was clicked, False if Cancel was clicked)
                if not result:
                    # User clicked Cancel - don't enable file logging
                    logger.info("File logging disclaimer denied.")
                    #uncheck the checkbox
                    self.settings.editable_settings_entries[SettingsKeys.ENABLE_FILE_LOGGER.value].set(0)
                    self.widgets[SettingsKeys.ENABLE_FILE_LOGGER.value].config(variable=self.settings.editable_settings_entries[SettingsKeys.ENABLE_FILE_LOGGER.value])  # Disable the checkbox

        # add a trace to the checkbox on change determine if we need to display disclaimer
        self.settings.editable_settings_entries[SettingsKeys.ENABLE_FILE_LOGGER.value].trace_add("write", _on_file_logger_click)

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

    def generate_whisper_model_list(self, system_ram, system_vram):
        """
        Generates a list of Whisper models with recommendations based on system capabilities.

        Args:
            system_ram (float): Available system RAM in GB
            system_vram (float): Available system VRAM in GB

        Returns:
            tuple: (display_options, actual_values, mapping_dict)
        """
        # Define model requirements
        whisper_models = [
            WhisperModelEnum("tiny", 8, 0, "tiny"),
            WhisperModelEnum("tiny.en", 8, 0, "tiny.en"),
            WhisperModelEnum("base", 8, 0, "base"),
            WhisperModelEnum("base.en", 8, 0, "base.en"),
            WhisperModelEnum("small", 8, 0, "small"),
            WhisperModelEnum("small.en", 8, 0, "small.en"),
            WhisperModelEnum("medium", 16, 0, "medium"),
            WhisperModelEnum("medium.en", 16, 0, "medium.en"),
            WhisperModelEnum("turbo", 16, 6, "turbo"),
            WhisperModelEnum("large", 16, 10, "large"),
        ]

        # Create display options with recommendations
        whisper_models_display = []
        whisper_models_values = []
        whisper_model_mapping = {}

        for model in whisper_models:
            display_name = model.name

            # logic to properly handle CPU-only models
            ram_sufficient = system_ram >= model.ram
            vram_sufficient = model.vram == 0 or system_vram >= model.vram

            if ram_sufficient and vram_sufficient:
                display_name = f"{model.display} ✓"
            else:
                display_name = f"{model.display} ⚠️"

            whisper_models_display.append(display_name)
            whisper_models_values.append(model.name)
            whisper_model_mapping[display_name] = model.name

        return whisper_models_display, whisper_models_values, whisper_model_mapping

    def create_whisper_settings(self):
        """
        Creates the Whisper settings UI elements in a two-column layout.
        Settings alternate between left and right columns for even distribution.
        Displays model recommendations based on system RAM and VRAM.
        """
        left_frame = ttk.Frame(self.whisper_settings_frame)
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")


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
        
        # Get system RAM and VRAM
        system_ram = get_system_memory()
        system_vram = get_system_vram()
        
        # Create the whisper model dropdown selection with recommendations
        tk.Label(left_frame, text=SettingsKeys.WHISPER_MODEL.value).grid(row=3, column=0, padx=0, pady=5, sticky="w")

        # Generate model list with recommendations
        whisper_models_display, whisper_models_values, whisper_model_mapping = self.generate_whisper_model_list(system_ram, system_vram)
        
        # Create a variable to store the selected model value (not display text)
        self.selected_whisper_model = tk.StringVar()
        
        self.whisper_models_drop_down = ttk.Combobox(left_frame, textvariable=self.selected_whisper_model, width=SHORT_ENTRY_WIDTH)
        self.whisper_models_drop_down['values'] = whisper_models_display
        self.whisper_models_drop_down.grid(row=3, column=1, padx=0, pady=5, sticky="w")
        
        # Store the mapping from display text to actual model value
        self.whisper_model_mapping = whisper_model_mapping
        
        # Add a trace to update the actual value when selection changes
        def update_whisper_model_value(*args):
            display_text = self.whisper_models_drop_down.get()
            actual_value = self.whisper_model_mapping.get(display_text, display_text.split()[0])
            self.selected_whisper_model.set(actual_value)
        
        self.whisper_models_drop_down.bind("<<ComboboxSelected>>", update_whisper_model_value)

        try:
            # Try to set the whisper model dropdown to the current model
            current_model = self.settings.editable_settings[SettingsKeys.WHISPER_MODEL.value]
            # Find the display option that corresponds to the current model
            for display_option in whisper_models_display:
                if display_option.startswith(f"{current_model} ") or display_option == current_model:
                    self.whisper_models_drop_down.set(display_option)
                    break
            else:
                # If not found, just set the raw value
                self.whisper_models_drop_down.set(current_model)
        except ValueError:
            # If error, set to first option
            if whisper_models_display:
                self.whisper_models_drop_down.set(whisper_models_display[0])
        
        # Store the actual model value, not the display text
        self.settings.editable_settings_entries[SettingsKeys.WHISPER_MODEL.value] = self.selected_whisper_model
        
        # Whisper Architecture Dropdown
        right_row += 1
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
        self.models_drop_down = ttk.Combobox(left_frame, values=models_drop_down_options, state="readonly")
        self.models_drop_down.grid(row=left_row, column=1, padx=0, pady=5, sticky="ew")
        self.models_drop_down.bind('<<ComboboxSelected>>', self.on_model_selection_change)
        thread = threading.Thread(target=self.settings.update_models_dropdown, args=(self.models_drop_down,))
        thread.start()

        # Create custom model entry (initially hidden)
        self.custom_model_entry = tk.Entry(left_frame, width=15)
        self.custom_model_entry.insert(0, self.settings.editable_settings[SettingsKeys.LOCAL_LLM_MODEL.value])

        refresh_button = ttk.Button(left_frame, text="↻", 
                                command=lambda: (self.save_settings(False), threading.Thread(target=self.settings.update_models_dropdown, args=(self.models_drop_down,)).start(), self.on_model_selection_change(None)), 
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
        Handle switching between model dropdown and custom model entry.
        
        When "Custom" is selected, shows a text entry field and hides the dropdown.
        When another model is selected, shows the dropdown and hides the custom entry.
        
        Args:
            event: The dropdown selection change event
            
        Notes:
            - Uses grid_info() to check if widgets are currently displayed
            - Preserves the row position when swapping widgets
            - Resets dropdown to placeholder when showing custom entry
        """
        if self.models_drop_down.get() == "Custom" and self.custom_model_entry.grid_info() == {}:
            # Show the custom model entry below the dropdown
            self.custom_model_entry.grid(row=self.models_drop_down.grid_info()['row'], 
                        column=1, padx=0, pady=5, sticky="w")
            self.models_drop_down.set("Select a Model")
            self.models_drop_down.grid_remove()
        elif self.models_drop_down.get() != "Custom" and self.custom_model_entry.grid_info() != {}:
            # Hide the custom model entry
            self.models_drop_down.grid(row=self.custom_model_entry.grid_info()['row'], 
                        column=1, padx=0, pady=5, sticky="w")
            self.custom_model_entry.grid_remove()

    def get_selected_model(self):
        """Returns the selected model, either from dropdown or custom entry"""
        if self.models_drop_down.get() in ["Custom", "Select a Model"]:
            return self.custom_model_entry.get()
        return self.models_drop_down.get()

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

            value = self.settings.editable_settings[setting_name]
            if value in [True, False]:
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

        def create_processing_section(label_text, setting_key, text_content, row):
            frame = tk.Frame(self.advanced_settings_frame, width=800)
            frame.grid(row=row, column=0, padx=10, pady=0, sticky="nw")
            self._create_checkbox(frame, f"Use {label_text}", setting_key, 0)
            row += 1
            
            text_area, row = self._create_text_area(self.advanced_settings_frame, label_text, text_content, row)
            return text_area, row

        row = self._create_section_header("⚠️ Advanced Settings (For Advanced Users Only)", 0, text_colour="red", frame=self.advanced_settings_frame)
        
        # General Settings
        if len(self.settings.adv_general_settings) > 0:
            row = self._create_section_header("General Settings", row, text_colour="black", frame=self.advanced_settings_frame)
            row = create_settings_columns(self.settings.adv_general_settings, row)

        # Whisper Settings
        row = self._create_section_header("Whisper Settings", row, text_colour="black", frame=self.advanced_settings_frame)
        left_frame = ttk.Frame(self.advanced_settings_frame)
        left_frame.grid(row=row, column=0, padx=10, pady=5, sticky="nw")
        right_frame = ttk.Frame(self.advanced_settings_frame)
        right_frame.grid(row=row, column=1, padx=10, pady=5, sticky="nw")
        
        self.create_editable_settings_col(left_frame, right_frame, 0, 0, self.settings.adv_whisper_settings)
        
        # # Audio meter
        # tk.Label(left_frame, text="Whisper Audio Cutoff").grid(row=1, column=0, padx=0, pady=0, sticky="w")
        # self.cutoff_slider = AudioMeter(left_frame, width=150, height=50, 
        #                             threshold=self.settings.editable_settings["Silence cut-off"] * 32768)
        # self.cutoff_slider.grid(row=1, column=1, padx=0, pady=0, sticky="w")
        row += 1

        # AI Settings
        row = self._create_section_header("AI Settings", row, text_colour="black", frame=self.advanced_settings_frame)
        row = create_settings_columns(self.settings.adv_ai_settings, row)
        
        # Prompting Settings
        row = self._create_section_header("Prompting Settings", row, text_colour="black", frame=self.advanced_settings_frame)

        # Pre convo instruction
        self.aiscribe_text, label_row1, text_row1, row = self._create_text_area(
            self.advanced_settings_frame, "Pre Conversation Instruction", self.settings.AISCRIBE, row
        )

        # Explanation for Pre convo instruction
        pre_explanation = (
            "This is the FIRST part of the AI prompt structure:\n\n"
            "• Acts as the opening instruction to the AI\n"
            "• Sets up how to interpret the conversation\n"
            "• Defines SOAP note format requirements\n"
            "• Conversation will be inserted after this\n\n"
            "⚠️ Modify with caution as it affects AI output quality"
        )
        tk.Label(
            self.advanced_settings_frame,
            text=pre_explanation,
            justify="left",
            font=("Arial", 9),
            fg="#272927"
        ).grid(row=text_row1, column=1, padx=(10, 0), pady=5, sticky="nw")

        # Post convo instruction
        self.aiscribe2_text, label_row2, text_row2, row = self._create_text_area(
            self.advanced_settings_frame, "Post Conversation Instruction", self.settings.AISCRIBE2, row
        )

        # Explanation for Post convo instruction
        post_explanation = (
            "This is the LAST part of the AI prompt structure:\n\n"
            "• Added after the conversation text\n"
            "• Provides final formatting instructions\n"
            "• Ensures SOAP note completeness\n"
            "• Helps maintain consistency\n\n"
            "⚠️ Modify with caution as it affects AI output quality"
        )
        tk.Label(
            self.advanced_settings_frame,
            text=post_explanation,
            justify="left",           
            font=("Arial", 9),
            fg="#272927"
        ).grid(row=text_row2, column=1, padx=(10, 0), pady=5, sticky="nw")

        if FeatureToggle.PRE_PROCESSING is True:
            # Processing Sections
            self.preprocess_text, row = create_processing_section(
                "Pre-Processing", 
                "Use Pre-Processing",
                self.settings.editable_settings["Pre-Processing"],
                row
            )
        
        if FeatureToggle.POST_PROCESSING is True:
            self.postprocess_text, _ = create_processing_section(
                "Post-Processing (Experimental. Use with caution.)",
                "Use Post-Processing", 
                self.settings.editable_settings["Post-Processing"],
                row
            )


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
        )
        
        self.__initialize_file_logger()

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

        self.settings.save_settings(
            self.openai_api_key_entry.get(),
            self.aiscribe_text.get("1.0", "end-1c"), # end-1c removes the trailing newline
            self.aiscribe2_text.get("1.0", "end-1c"), # end-1c removes the trailing newline
            self.settings_window,
            # self.api_dropdown.get(),
            self.settings.editable_settings["Silence cut-off"], # Save the old one for whisper audio cutoff, will be removed in future, left in incase we go back to old cut off
            # self.cutoff_slider.threshold / 32768, # old threshold 
        )
        # send load event after the settings are saved
        if update_whisper_model_flag:
            self.main_window.root.event_generate("<<LoadSttModel>>")
        # unload whisper model if switched to remote
        if not self.settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]:
            self.main_window.root.event_generate("<<UnloadSttModel>>")
        # unload / reload model after the settings are saved
        if local_model_unload_flag:
            logging.debug("unloading ai model")
            ModelManager.unload_model()
        if local_model_reload_flag:
            logging.debug("reloading ai model")
            ModelManager.start_model_threaded(self.settings, self.main_window.root)

        if self.settings.editable_settings["Use Docker Status Bar"] and self.main_window.docker_status_bar is None:
            self.main_window.create_docker_status_bar()
        elif not self.settings.editable_settings["Use Docker Status Bar"] and self.main_window.docker_status_bar is not None:
            self.main_window.destroy_docker_status_bar()

        if self.settings.editable_settings["Enable Scribe Template"]:
            self.main_window.create_scribe_template()
        else:
            self.main_window.destroy_scribe_template()

        if close_window:
            self.close_window()

    def __initialize_file_logger(self):
        # if un changed, do nothing
        logger.info("Checking file logging setting...")
        if self.settings.editable_settings_entries[SettingsKeys.ENABLE_FILE_LOGGER.value].get() == self.settings.editable_settings[SettingsKeys.ENABLE_FILE_LOGGER.value]:
            logger.info("File logging setting unchanged.")
            return

        if self.settings.editable_settings_entries[SettingsKeys.ENABLE_FILE_LOGGER.value].get() == 1:
            utils.log_config.add_file_handler(utils.log_config.logger, utils.log_config.formatter)
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
        frame, row = self.create_editable_settings(self.general_settings_frame, self.settings.general_settings)
        
        # Add a note at the bottom of the general settings frame
        note_text = (
        "NOTE: To protect personal health information (PHI), we recommend using a local network.\n"
        "The 'Show Scrub PHI' feature is only applicable for local LLMs and private networks.\n"
        "For internet-facing endpoints, this feature will always be enabled, regardless of the 'Show Scrub PHI' setting."
    )

        # Create a frame to hold the note labels
        note_frame = tk.Frame(self.general_settings_frame)
        note_frame.grid(padx=10, pady=5, sticky="w")

        # Add the red * label
        star_label = tk.Label(note_frame, text="*", fg="red", font=("Arial", 10, "bold"))
        star_label.grid(row=0, column=0, sticky="w")

        # Add the rest of the text in black (bold and underlined)
        note_label = tk.Label(
            note_frame,
            text=note_text,
            fg="black",  # Set text color to black
            font=("Arial", 8, "bold underline"),  # Set font to bold and underlined
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
        value = tk.IntVar(value=int(self.settings.editable_settings[setting_name]))
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
        # Guard clause: return frame as is if it's not the advanced frame
        if frame != self.advanced_frame:
            return frame

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
