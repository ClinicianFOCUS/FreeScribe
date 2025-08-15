"""
application_settings.py

This software is released under the AGPL-3.0 license
Copyright (c) 2023-2024 Braedon Hendy

Further updates and packaging added in 2024 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform". 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students - Software Developer Alex Simko, Pemba Sherpa (F24), and Naitik Patel.

This module contains the ApplicationSettings class, which manages the settings for an
application that involves audio processing and external API interactions, including
WhisperAudio, and OpenAI services.

"""

import json
import os
import tkinter as tk
from tkinter import messagebox
import requests
import logging
from typing import List, Any, Optional

from UI.SettingsConstant import SettingsKeys, Architectures, FeatureToggle, DEFAULT_CONTEXT_WINDOW_SIZE
from utils.file_utils import get_resource_path, get_file_path
from utils.utils import get_application_version
from utils.ip_utils import is_valid_url
import multiprocessing
import utils.whisper.Constants
from utils.log_config import logger

class SettingsWindow():
    """
    Manages application settings related to audio processing and external API services.

    Attributes
    ----------
    OPENAI_API_KEY : str
        The API key for OpenAI integration.
        Placeholder for the second AI Scribe settings.
    # API_STYLE : str FUTURE FEATURE REVISION
    #     The API style to be used (default is 'OpenAI'). FUTURE FEATURE

    editable_settings : dict
        A dictionary containing user-editable settings such as model parameters, audio 
        settings, and real-time processing configurations.
    
    setting_types : dict
        A dictionary mapping setting keys to their expected types (bool, int, or str).
    
    Methods
    -------
    load_settings_from_file():
        Loads settings from a JSON file and updates the internal state.
    save_settings_to_file():
        Saves the current settings to a JSON file.
    save_settings(openai_api_key, settings_window):
        Saves the current settings, including API keys, IP addresses, and user-defined parameters.
    clear_settings_file(settings_window):
        Clears the content of settings files and closes the settings window.
    """

    CPU_INSTALL_FILE = "CPU_INSTALL.txt"
    NVIDIA_INSTALL_FILE = "NVIDIA_INSTALL.txt"
    STATE_FILES_DIR = "install_state"
    DEFAULT_WHISPER_ARCHITECTURE = Architectures.CPU.architecture_value
    DEFAULT_LLM_ARCHITECTURE = Architectures.CPU.architecture_value
    AUTO_DETECT_LANGUAGE_CODES = ["", " ","auto", "Auto Detect", "None", "None (Auto Detect)"]

    DEFAULT_SETTINGS_TABLE = {
            SettingsKeys.LOCAL_LLM_MODEL.value: "gemma2:2b-instruct-q8_0",
            SettingsKeys.LLM_ENDPOINT.value: "https://localhost:3334/v1",
            SettingsKeys.LOCAL_LLM.value: True,
            SettingsKeys.LLM_ARCHITECTURE.value: DEFAULT_LLM_ARCHITECTURE,
            SettingsKeys.LOCAL_LLM_CONTEXT_WINDOW.value: DEFAULT_CONTEXT_WINDOW_SIZE,
            "use_story": False,
            "use_memory": False,
            "use_authors_note": False,
            "use_world_info": False,
            "max_context_length": 5000,
            "max_length": 400,
            "rep_pen": 1.1,
            "rep_pen_range": 5000,
            "rep_pen_slope": 0.7,
            "temperature": 0.1,
            "tfs": 0.97,
            "top_a": 0.8,
            "top_k": 30,
            "top_p": 0.4,
            "typical": 0.19,
            "sampler_order": "[6, 0, 1, 3, 4, 2, 5]",
            "singleline": False,
            "frmttriminc": False,
            "frmtrmblln": False,
            SettingsKeys.LOCAL_WHISPER.value: True,
            SettingsKeys.WHISPER_ENDPOINT.value: "https://localhost:2224/whisperaudio",
            SettingsKeys.WHISPER_SERVER_API_KEY.value: "",
            SettingsKeys.WHISPER_ARCHITECTURE.value: DEFAULT_WHISPER_ARCHITECTURE,
            SettingsKeys.WHISPER_BEAM_SIZE.value: 5,
            SettingsKeys.WHISPER_CPU_COUNT.value: multiprocessing.cpu_count(),
            SettingsKeys.WHISPER_VAD_FILTER.value: True,
            SettingsKeys.WHISPER_COMPUTE_TYPE.value: "float16",
            SettingsKeys.WHISPER_MODEL.value: utils.whisper.Constants.WhisperModels.SMALL_EN.label,
            "Current Mic": "None",
            SettingsKeys.WHISPER_REAL_TIME.value: True,
            "Real Time Audio Length": 3,
            "Real Time Silence Length": 1.1,
            "Silence cut-off": 0.035,
            "LLM Container Name": "ollama",
            "LLM Caddy Container Name": "caddy-ollama",
            "LLM Authentication Container Name": "authentication-ollama",
            "Whisper Container Name": "speech-container",
            "Whisper Caddy Container Name": "caddy",
            "Auto Shutdown Containers on Exit": True,
            "Use Docker Status Bar": False,
            "Show Welcome Message": True,
            SettingsKeys.USE_PRE_PROCESSING.value: False,
            "Use Post-Processing": FeatureToggle.POST_PROCESSING,
            "AI Server Self-Signed Certificates": False,
            SettingsKeys.S2T_SELF_SIGNED_CERT.value: False,
            "Pre-Processing": "Please break down the conversation into a list of facts. Take the conversation and transform it to a easy to read list:\n\n",
            "Post-Processing": "\n\nUsing the provided list of facts, review the SOAP note for accuracy. Verify that all details align with the information provided in the list of facts and ensure consistency throughout. Update or adjust the SOAP note as necessary to reflect the listed facts without offering opinions or subjective commentary. Ensure that the revised note excludes a \"Notes\" section and does not include a header for the SOAP note. Provide the revised note after making any necessary corrections.",
            "Show Scrub PHI": False,
            SettingsKeys.AUDIO_PROCESSING_TIMEOUT_LENGTH.value: 180,
            SettingsKeys.SILERO_SPEECH_THRESHOLD.value: 0.75,
            SettingsKeys.USE_TRANSLATE_TASK.value: False,
            SettingsKeys.WHISPER_LANGUAGE_CODE.value: "None (Auto Detect)",
            SettingsKeys.Enable_Word_Count_Validation.value : True,  # Default to enabled
            SettingsKeys.Enable_AI_Conversation_Validation.value : False,  # Default to disabled
            SettingsKeys.USE_LOW_MEM_MODE.value: False,
            SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value : False,
            SettingsKeys.FACTUAL_CONSISTENCY_VERIFICATION.value: False,
            # Best of N (Experimental), by default we only generate 1 completion of note, if this is set to a number greater than 1, we will generate N completions and pick the best one.
            SettingsKeys.BEST_OF.value: 1,
            # Google Maps API settings
            SettingsKeys.GOOGLE_MAPS_API_KEY.value: "",  # Will be set by user
            SettingsKeys.ENABLE_FILE_LOGGER.value: False,
            SettingsKeys.STORE_NOTES_LOCALLY.value: False,
            SettingsKeys.STORE_RECORDINGS_LOCALLY.value: False,
            SettingsKeys.WHISPER_INITIAL_PROMPT.value: "None",
            # Best of N (Experimental), by default we only generate 1 completion of note, if this is set to a number greater than 1, we will generate N completions and pick the best one.
            SettingsKeys.BEST_OF.value: 1,
        }

    def __init__(self):
        """Initializes the ApplicationSettings with default values."""
        self.OPENAI_API_KEY = "None"
        # self.API_STYLE = "OpenAI" # FUTURE FEATURE REVISION
        self.main_window = None
        
        # Initialize setting types dictionary
        self.setting_types = {}
        for key, value in self.DEFAULT_SETTINGS_TABLE.items():
            if isinstance(value, bool):
                self.setting_types[key] = bool
            elif isinstance(value, int):
                self.setting_types[key] = int
            elif isinstance(value, float):
                self.setting_types[key] = float
            else:
                self.setting_types[key] = str

        self.general_settings = [
            "Show Welcome Message",
            "BlankSpace",
            "Show Scrub PHI",      
        ]

        self.whisper_settings = [
            "BlankSpace", # Represents the SettingsKeys.LOCAL_WHISPER.value checkbox that is manually placed
            SettingsKeys.WHISPER_REAL_TIME.value,
            "BlankSpace", # Represents the model dropdown that is manually placed
            "BlankSpace", # Represents the mic dropdown
            SettingsKeys.WHISPER_ENDPOINT.value,
            SettingsKeys.WHISPER_SERVER_API_KEY.value,
            "BlankSpace", # Represents the architecture dropdown that is manually placed
            SettingsKeys.S2T_SELF_SIGNED_CERT.value,
        ]

        self.llm_settings = [
            SettingsKeys.LLM_ENDPOINT.value,
            "AI Server Self-Signed Certificates",
        ]

        self.adv_ai_settings = [
            ##############################################################################################
            # Stuff that is commented is related to KobolodCPP API and not used in the current version   #
            # Maybe use it in the future? commented out for now, goes hand in hand with API style        #
            ##############################################################################################

            # "use_story",
            # "use_memory",
            # "use_authors_note",
            # "use_world_info",
            # "max_context_length",
            # "max_length",
            # "rep_pen",
            # "rep_pen_range",
            # "rep_pen_slope",
            "temperature",
            "tfs",
            # "top_a",
            "top_k",
            "top_p",
            # "typical",
            # "sampler_order",
            # "singleline",
            # "frmttriminc",
            # "frmtrmblln",
            SettingsKeys.LOCAL_LLM_CONTEXT_WINDOW.value,
            SettingsKeys.Enable_Word_Count_Validation.value,
            SettingsKeys.USE_PRE_PROCESSING.value,

        ]
        
        if FeatureToggle.LLM_CONVO_PRESCREEN:
            self.adv_ai_settings.append(SettingsKeys.Enable_AI_Conversation_Validation.value)

        if FeatureToggle.BEST_OF:
            self.adv_ai_settings.append(SettingsKeys.BEST_OF.value)

        if FeatureToggle.FACTS_CHECK:
            self.adv_ai_settings.append(SettingsKeys.FACTUAL_CONSISTENCY_VERIFICATION.value)

        self.adv_whisper_settings = [
            # "Real Time Audio Length",
            # "BlankSpace", # Represents the whisper cuttoff
            SettingsKeys.WHISPER_BEAM_SIZE.value,
            SettingsKeys.WHISPER_CPU_COUNT.value,
            # SettingsKeys.WHISPER_VAD_FILTER.value,
            SettingsKeys.WHISPER_COMPUTE_TYPE.value,
            "Real Time Audio Length",
            # left out for now, dont need users tinkering and default is good and tested.
            # SettingsKeys.SILERO_SPEECH_THRESHOLD.value, 
            SettingsKeys.USE_TRANSLATE_TASK.value,
            SettingsKeys.WHISPER_LANGUAGE_CODE.value,
        ]

        if FeatureToggle.HALLUCINATION_CLEANING:
            self.adv_whisper_settings.append(SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value)


        self.adv_general_settings = [
            SettingsKeys.AUDIO_PROCESSING_TIMEOUT_LENGTH.value,
            SettingsKeys.STORE_RECORDINGS_LOCALLY.value,
            SettingsKeys.STORE_NOTES_LOCALLY.value,
            SettingsKeys.ENABLE_FILE_LOGGER.value,
            SettingsKeys.USE_LOW_MEM_MODE.value,
        ]

        self.developer_settings = [
            "Real Time Silence Length",
            "BlankSpace", # Represents the Whisper Initial Prompt
            SettingsKeys.Enable_AI_Conversation_Validation.value,
            SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value,
        ]

        self.editable_settings = SettingsWindow.DEFAULT_SETTINGS_TABLE

        self.docker_settings = [
            "LLM Container Name",
            "LLM Caddy Container Name",
            "LLM Authentication Container Name",
            "Whisper Container Name",
            "Whisper Caddy Container Name",
            "Auto Shutdown Containers on Exit",
            "Use Docker Status Bar",
        ]
        # saves newest value, but not saved to config file yet
        self.editable_settings_entries = {}
        self.load_settings_from_file()
        self._create_settings_and_aiscribe_if_not_exist()    
        
    def convert_setting_value(self, setting: str, value: Any) -> Any:
        """
        Convert a setting value to the appropriate type based on the setting name.
        
        This helper method determines the correct type conversion for a setting value
        based on the type information stored in setting_types.
        
        :param setting: The name of the setting
        :type setting: str
        :param value: The value to convert
        :type value: Any
        :returns: The converted value
        :rtype: Any
        """
        if setting not in self.setting_types:
            return value
            
        target_type = self.setting_types[setting]
        
        # If value is already the correct type, return it
        if isinstance(value, target_type):
            return value
            
        try:
            if target_type == bool:
                # Convert to boolean (handles both int and string representations)
                return bool(int(value) if isinstance(value, str) else value)
            elif target_type in (int, float):
                return target_type(value)
            else:
                return str(value)
        except (ValueError, TypeError):
            logging.warning(f"Warning: Could not convert {setting} value to {target_type}")

            return value

    def load_settings_from_file(self, filename='settings.txt'):
        """
        Loads settings from a JSON file.

        The settings are read from 'settings.txt'. If the file does not exist or cannot be parsed,
        default settings will be used. The method updates the instance attributes with loaded values.

        Returns:
            tuple: A tuple containing the IPs, ports, SSL settings, and API key.
        """
        try:
            with open(get_resource_path(filename), 'r') as file:
                try:
                    settings = json.load(file)
                except json.JSONDecodeError:
                    logger.exception("Failed to decode JSON from settings file")
                    return self.OPENAI_API_KEY

                self.OPENAI_API_KEY = settings.get("openai_api_key", self.OPENAI_API_KEY)
                # self.API_STYLE = settings.get("api_style", self.API_STYLE) # FUTURE FEATURE REVISION
                loaded_editable_settings = settings.get("editable_settings", {})
                
                for key, value in loaded_editable_settings.items():
                    if key in self.editable_settings:
                        # Convert the value to the appropriate type based on the setting name
                        self.editable_settings[key] = self.convert_setting_value(key, value)

                if self.editable_settings["Use Docker Status Bar"] and self.main_window is not None:
                    self.main_window.create_docker_status_bar()
                            
                return self.OPENAI_API_KEY
        except FileNotFoundError:
            logger.info("Settings file not found. Using default settings.")
            self.save_settings_to_file()
            return self.OPENAI_API_KEY
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return self.OPENAI_API_KEY

    def save_settings_to_file(self):
        """
        Saves the current settings to a JSON file.

        The settings are written to 'settings.txt'. This includes all application settings 
        such as IP addresses, ports, SSL settings, and editable settings.

        Returns:
            None
        """
        settings = {
            "openai_api_key": self.OPENAI_API_KEY,
            "editable_settings": self.editable_settings,
            # "api_style": self.API_STYLE # FUTURE FEATURE REVISION
            "app_version": get_application_version()
        }
        with open(get_resource_path('settings.txt'), 'w') as file:
            json.dump(settings, file)

    def save_settings(self, openai_api_key, settings_window,
                    silence_cutoff):
        """
        Save the current settings, including IP addresses, API keys, and user-defined parameters.

        This method writes the AI Scribe text to separate text files and updates the internal state
        of the Settings instance.

        :param str openai_api_key: The OpenAI API key for authentication.
        :param tk.Toplevel settings_window: The settings window instance to be destroyed after saving.
        """
        # Ensure no leading/trailing spaces
        self.OPENAI_API_KEY = openai_api_key.strip()
        # self.API_STYLE = api_style

        self.editable_settings["Silence cut-off"] = silence_cutoff

        for setting, entry in self.editable_settings_entries.items():     
            value = entry.get()
            # Convert the value to the appropriate type based on the setting name
            self.editable_settings[setting] = self.convert_setting_value(setting, value)

            # trim any blank spaces or new char lines for endpoints and API keys
            if setting in [SettingsKeys.LLM_ENDPOINT.value, 
                          SettingsKeys.WHISPER_ENDPOINT.value,
                          SettingsKeys.WHISPER_SERVER_API_KEY.value]:
                value = entry.get()
                self.editable_settings[setting] = value.strip()


        self.save_settings_to_file()

        ret_value = True

        return ret_value

    def __clear_settings_file(self):
        """
        Clears the content of settings files and closes the settings window.
        """
        # Open the files and immediately close them to clear their contents.
        open(get_resource_path('settings.txt'), 'w').close()  
        logger.info("Settings file cleared.")

    def __keep_network_clear_settings(self):
        """
        Clears the content of settings files while maintaining network settings.
        Such as API keys and endpoints.
        This method is intended for internal use only.
        """
        # Keep the network settings and clear the rest
        settings_to_keep = {
            SettingsKeys.LLM_ENDPOINT.value: self.editable_settings[SettingsKeys.LLM_ENDPOINT.value],
            "AI Server Self-Signed Certificates": self.editable_settings["AI Server Self-Signed Certificates"],
            SettingsKeys.LOCAL_LLM.value: self.editable_settings[SettingsKeys.LOCAL_LLM.value],
            SettingsKeys.LOCAL_WHISPER.value: self.editable_settings[SettingsKeys.LOCAL_WHISPER.value],
            SettingsKeys.WHISPER_ENDPOINT.value: self.editable_settings[SettingsKeys.WHISPER_ENDPOINT.value],
            SettingsKeys.WHISPER_SERVER_API_KEY.value: self.editable_settings[SettingsKeys.WHISPER_SERVER_API_KEY.value],
            SettingsKeys.S2T_SELF_SIGNED_CERT.value: self.editable_settings[SettingsKeys.S2T_SELF_SIGNED_CERT.value],

        }
        
        # reset to defaults
        self.editable_settings = SettingsWindow.DEFAULT_SETTINGS_TABLE
        
        # Clear the AI scribe stuff to and empty the settings file
        self.__clear_settings_file()

        # Update the settings with the network settings
        self.editable_settings.update(settings_to_keep)
        logger.info("Settings file cleared except network settings.")

        # Save the settings to file
        self.save_settings_to_file()

    def clear_settings_file(self, settings_window, keep_network_settings=False):
        """
        Clears the content of settings files and closes the settings window.

        This method attempts to open and clear the contents of three text files:
        `settings.txt`. After clearing the
        files, it displays a message box to notify the user that the settings
        have been reset and closes the `settings_window`. If an error occurs
        during this process, the exception will be caught and printed.

        :param settings_window: The settings window object to be closed after resetting.
        :type settings_window: tkinter.Toplevel or similar
        :raises Exception: If there is an issue with file handling or window destruction.

        Example usage:

        """
        try:
            if keep_network_settings:
                self.__keep_network_clear_settings()
            else:
                self.__clear_settings_file()

            # Display a message box informing the user of successful reset.
            messagebox.showinfo("Settings Reset", "Settings have been reset. Please restart application. Unexpected behaviour may occur if you continue using the application.")

            # Close the settings window.
            settings_window.destroy()
        except Exception as e:
            # Print any exception that occurs during file handling or window destruction.
            logger.exception("Failed to clear settings file")
            messagebox.showerror("Error", "An error occurred while clearing settings. Please try again.")

    def get_available_models(self,endpoint=None):
        """
        Returns a list of available models for the user to choose from.

        This method returns a list of available models that can be used with the AI Scribe
        service. The list includes the default model, `gpt-4`, as well as any other models
        that may be added in the future.

        Returns:
            list: A list of available models for the user to choose from.
        """
        
        headers = {
            "Authorization": f"Bearer {self.OPENAI_API_KEY}",
            "X-API-Key": self.OPENAI_API_KEY
        }

        endpoint = endpoint or self.editable_settings_entries[SettingsKeys.LLM_ENDPOINT.value].get()

        # url validate the endpoint
        if not is_valid_url(endpoint):
            logger.info("Invalid LLM Endpoint")
            return ["Invalid LLM Endpoint", "Custom"]

        if endpoint.endswith("/"):
            endpoint = endpoint[:-1]

        try:
            verify = not self.editable_settings["AI Server Self-Signed Certificates"]
            response = requests.get(endpoint + "/models", headers=headers, verify=verify, timeout=10.0)
            response.raise_for_status()  # Raise an error for bad responses
            models = response.json().get("data", [])  # Extract the 'data' field
            
            if not models:
                return ["No models available", "Custom"]

            available_models = [model["id"] for model in models]
            available_models.append("Custom")
            return available_models
        except requests.RequestException as e:
            logger.exception("Failed to fetch models from endpoint")
            return ["Failed to load models", "Custom"]

    def update_models_dropdown(self, dropdown, endpoint=None):
        """
        Updates the models dropdown with the available models.

        This method fetches the available models from the AI Scribe service and updates
        the dropdown widget in the settings window with the new list of models.
        """
        if self.editable_settings_entries[SettingsKeys.LOCAL_LLM.value].get():
            return

        dropdown["values"] = ["Loading models...", "Custom"]
        dropdown.set("Loading models...")
        models = self.get_available_models(endpoint=endpoint)
        dropdown["values"] = models
        if self.editable_settings[SettingsKeys.LOCAL_LLM_MODEL.value] in models:
            dropdown.set(self.editable_settings[SettingsKeys.LOCAL_LLM_MODEL.value])
        else:
            dropdown.set(models[0])
        
    def set_main_window(self, window):
        """
        Set the main window instance for the settings.

        This method sets the main window instance for the settings class, allowing
        the settings to interact with the main window when necessary.

        Parameters:
            window (MainWindow): The main window instance to set.
        """
        self.main_window = window

    def load_or_unload_model(self, old_model, new_model, old_use_local_llm, new_use_local_llm, old_architecture, new_architecture,
                             old_context_window, new_context_window, old_low_mem, new_low_mem):
        """
        Determine if the model needs to be loaded or unloaded based on settings changes.

        This method compares old and new settings values to determine if the language model
        needs to be reloaded or unloaded. It returns two boolean flags indicating whether
        to unload the current model and whether to load a new model.

        :param old_model: The previously selected model name
        :type old_model: str
        :param new_model: The newly selected model name
        :type new_model: str
        :param old_use_local_llm: Previous state of local LLM checkbox (0=off, 1=on)
        :type old_use_local_llm: int
        :param new_use_local_llm: New state of local LLM checkbox (0=off, 1=on)
        :type new_use_local_llm: int
        :param old_architecture: Previously selected architecture
        :type old_architecture: str
        :param new_architecture: Newly selected architecture
        :type new_architecture: str
        :param old_context_window: Previous context window size
        :type old_context_window: int
        :param new_context_window: New context window size
        :type new_context_window: int
        :return: Tuple of (unload_flag, reload_flag) where:
                 - unload_flag: True if current model should be unloaded
                 - reload_flag: True if new model should be loaded
        :rtype: tuple(bool, bool)
        """
        unload_flag = False
        reload_flag = False
        try:
            if new_use_local_llm:
                if any([
                    old_use_local_llm != new_use_local_llm,
                    old_model != new_model,
                    old_architecture != new_architecture,
                    int(old_context_window) != int(new_context_window)]
                ):
                    reload_flag = True
            else:
                unload_flag = True
        # in case context_window value is invalid
        except (ValueError, TypeError) as e:
            logging.exception("Failed to determine reload/unload model")
        logging.info(f"load_or_unload_model {unload_flag=}, {reload_flag=}")
        return unload_flag, reload_flag


    def _create_settings_and_aiscribe_if_not_exist(self):
        """
        Ensure settings and AI Scribe files exist.
        - If settings.txt is missing or invalid, create it with default values.
        - If preserved_network_config.txt exists, transfer its network-related settings to settings.txt and delete it.
        """
        
        settings_path = get_resource_path('settings.txt')
        preserved_network_path = get_resource_path('preserved_network_config.txt')
        
        # Initialize settings with a default structure
        settings = {"editable_settings": {}}
        
        # Try to load existing settings if the file exists and is not empty
        if os.path.exists(settings_path) and os.path.getsize(settings_path) > 0:
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            except json.JSONDecodeError:
                print("settings.txt exists but contains invalid JSON. Creating new settings file.")
        else:
            print("settings.txt not found or empty. Creating with default values.")
            
        # Set default architecture if CUDA is available
        architectures = self.get_available_architectures()
        if Architectures.CUDA.label in architectures:
            settings["editable_settings"][SettingsKeys.WHISPER_ARCHITECTURE.value] = Architectures.CUDA.label
            settings["editable_settings"][SettingsKeys.LLM_ARCHITECTURE.value] = Architectures.CUDA.label
        
        # If preserved_network_config.txt exists, move network settings to settings.txt
        if os.path.exists(preserved_network_path):
            try:
                print("Found preserved_network_config.txt. Moving network settings to settings.txt.")
                
                # Load preserved network settings
                with open(preserved_network_path, 'r') as f:
                    preserved_config = json.load(f)
                
                preserved_network_config = preserved_config.get("editable_settings", {})
                
                # Extract only the relevant network settings
                settings_to_keep = {
                    SettingsKeys.LLM_ENDPOINT.value: preserved_network_config.get(SettingsKeys.LLM_ENDPOINT.value),
                    "AI Server Self-Signed Certificates": preserved_network_config.get("AI Server Self-Signed Certificates"),
                    SettingsKeys.LOCAL_LLM.value: preserved_network_config.get(SettingsKeys.LOCAL_LLM.value),
                    SettingsKeys.LOCAL_WHISPER.value: preserved_network_config.get(SettingsKeys.LOCAL_WHISPER.value),
                    SettingsKeys.WHISPER_ENDPOINT.value: preserved_network_config.get(SettingsKeys.WHISPER_ENDPOINT.value),
                    SettingsKeys.WHISPER_SERVER_API_KEY.value: preserved_network_config.get(SettingsKeys.WHISPER_SERVER_API_KEY.value),
                    SettingsKeys.S2T_SELF_SIGNED_CERT.value: preserved_network_config.get(SettingsKeys.S2T_SELF_SIGNED_CERT.value),
                }
                
                # Filter out None values
                settings_to_keep = {k: v for k, v in settings_to_keep.items() if v is not None}
                
                # Update settings with the extracted network values
                if "editable_settings" not in settings:
                    settings["editable_settings"] = {}
                settings["editable_settings"].update(settings_to_keep)
                
                # Remove preserved_network_config.txt after merging network settings
                os.remove(preserved_network_path)
                print("Deleted preserved_network_config.txt.")
            except json.JSONDecodeError:
                print("preserved_network_config.txt contains invalid JSON. Skipping import.")
            except Exception as e:
                print(f"Error processing preserved_network_config.txt: {str(e)}")
        
        # Update self.editable_settings from the settings dictionary
        self.editable_settings.update(settings.get("editable_settings", {}))
        
        # Save updated settings to file
        self.save_settings_to_file()
        
        ret_value = True

        return ret_value

    def get_available_architectures(self):
        """
        Returns a list of available architectures for the user to choose from.

        Based on the install state files in _internal folder

        Files must be named CPU_INSTALL or NVIDIA_INSTALL

        Returns:
            list: A list of available architectures for the user to choose from.
        """
        architectures = [Architectures.CPU.label]  # CPU is always available as fallback

        # Check for NVIDIA support
        if os.path.isfile(get_file_path(self.STATE_FILES_DIR, self.NVIDIA_INSTALL_FILE)):
            architectures.append(Architectures.CUDA.label)

        return architectures

    def update_whisper_model(self):
        # save the old whisper model to compare with the new model later
        old_local_whisper = self.editable_settings[SettingsKeys.LOCAL_WHISPER.value]
        old_whisper_architecture = self.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value]
        old_model = self.editable_settings[SettingsKeys.WHISPER_MODEL.value]
        old_cpu_count = self.editable_settings[SettingsKeys.WHISPER_CPU_COUNT.value]
        old_compute_type = self.editable_settings[SettingsKeys.WHISPER_COMPUTE_TYPE.value]

        new_low_mem = self.editable_settings_entries[SettingsKeys.USE_LOW_MEM_MODE.value].get()

        # IF unchecked then we need to load the model
        if bool(new_low_mem):
            return False

        # loading the model after the window is closed to prevent the window from freezing
        # if Local Whisper is selected, compare the old model with the new model and reload the model if it has changed
        # if switched from remote to local whisper
        if not old_local_whisper and self.editable_settings_entries[SettingsKeys.LOCAL_WHISPER.value].get():
            return True
        # new settings of LOCAL_WHISPER should be True, or we can skip reloading
        if self.editable_settings_entries[SettingsKeys.LOCAL_WHISPER.value].get() and (
                old_model != self.editable_settings_entries[SettingsKeys.WHISPER_MODEL.value].get() or
                old_whisper_architecture != self.editable_settings_entries[SettingsKeys.WHISPER_ARCHITECTURE.value].get() or
                int(old_cpu_count) != int(self.editable_settings_entries[SettingsKeys.WHISPER_CPU_COUNT.value].get()) or
                old_compute_type != self.editable_settings_entries[SettingsKeys.WHISPER_COMPUTE_TYPE.value].get()
        ):
            return True
        return False

    def is_low_mem_mode(self):
        """
        Returns the value of the 'Use Low Memory Mode' setting.
        
        Returns:
            bool: The value of the 'Use Low Memory Mode' setting
        """
        return self.editable_settings[SettingsKeys.USE_LOW_MEM_MODE.value]