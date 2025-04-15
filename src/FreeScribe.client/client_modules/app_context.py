import queue
import threading
import tkinter as tk

import torch
import pyaudio

from UI.MainWindowUI import MainWindowUI
from UI.SettingsWindow import SettingsWindow
from utils.OneInstance import OneInstance


class AppConstants:
    APP_NAME = 'AI Medical Scribe'  # Application name
    APP_TASK_MANAGER_NAME = 'freescribe-client.exe'
    NOTE_CREATION = "Note Creation...Please Wait"
    SILENCE_WARNING_LENGTH = 10  # seconds, warn the user after 10s of no input something might be wrong
    CHUNK = 512
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    DEFAULT_BUTTON_COLOUR = "SystemButtonFace"


class AppContext:
    """
    shared moving parts
    """
    # check if another instance of the application is already running.
    # if false, create a new instance of the application
    # if true, exit the current instance
    app_manager = OneInstance(AppConstants.APP_NAME, AppConstants.APP_TASK_MANAGER_NAME)
    root = tk.Tk()
    # settings logic
    app_settings = SettingsWindow()
    #  create our ui elements and settings config
    window = MainWindowUI(root, app_settings)
    user_message = []
    response_history = []
    IS_FIRST_LOG = True
    current_view = "full"
    uploaded_file_path = None
    is_recording = False
    recording_thread = None
    is_realtimeactive = False
    frames = []
    is_paused = False
    is_flashing = False
    use_aiscribe = True
    p = pyaudio.PyAudio()
    audio_queue = queue.Queue()
    silent_warning_duration = 0
    # Application flags
    is_audio_processing_realtime_canceled = threading.Event()
    is_audio_processing_whole_canceled = threading.Event()
    cancel_await_thread = threading.Event()
    # Thread tracking variables
    realtime_transcribe_thread_id = None
    generation_thread_id = None
    # Global instance of whisper model
    stt_local_model = None
    stt_model_loading_thread_lock = threading.Lock()
    silero, _silero = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
    # Initialize variables to store window geometry for switching between views
    last_full_position = None
    last_minimal_position = None


class AppUIComponents:
    user_input = None
    response_display = None
    send_button = None
    clear_button = None
    upload_button = None
    mic_button = None
    pause_button = None
    switch_view_button = None
    blinking_circle_canvas = None
    footer_frame = None
    timestamp_listbox = None
    mic_test = None
    history_frame = None
    circle = None
