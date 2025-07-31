"""
This software is released under the AGPL-3.0 license
Copyright (c) 2023-2024 Braedon Hendy

Further updates and packaging added in 2024 through the ClinicianFOCUS initiative,
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied
Learning and Technology as part of the CNERG+ applied research project,
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform".
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner),
and Research Students - Software Developer Alex Simko, Pemba Sherpa (F24), and Naitik Patel.

"""

import ctypes
import io
import sys
import gc
import os
import logging
from pathlib import Path
import wave
import threading
import json
import datetime
import re
import time
import queue
import atexit
import torch
import pyaudio
import requests
import pyperclip
import speech_recognition as sr  # python package is named speechrecognition
import scrubadub
import numpy as np
import tkinter as tk
import math
import traceback
import asyncio
from tkinter import ttk, filedialog
import tkinter.messagebox as messagebox
import librosa
from faster_whisper import WhisperModel
from UI.MainWindowUI import MainWindowUI
from UI.SettingsWindow import SettingsWindow
from UI.SettingsConstant import SettingsKeys, FeatureToggle
from UI.Widgets.CustomTextBox import CustomTextBox
from UI.LoadingWindow import LoadingWindow
from UI.ImageWindow import ImageWindow
from Model import ModelManager
from utils.ip_utils import is_private_ip
from utils.file_utils import get_file_path, get_resource_path
from utils.OneInstance import OneInstance
from utils.utils import get_application_version
import utils.AESCryptoUtils as AESCryptoUtils
import utils.audio
import utils.AESCryptoUtils as AESCryptoUtils
import utils.system
from UI.Widgets.MicrophoneTestFrame import MicrophoneTestFrame
from utils.windows_utils import remove_min_max, add_min_max
from WhisperModel import TranscribeError
from UI.Widgets.PopupBox import PopupBox
from UI.Widgets.TimestampListbox import TimestampListbox
from UI.RecordingsManager import RecordingsManager
from UI.ScrubWindow import ScrubWindow
from utils.log_config import logger
from Model import ModelStatus
from services.whisper_hallucination_cleaner import hallucination_cleaner
from utils.whisper.WhisperModel import load_stt_model, faster_whisper_transcribe, is_whisper_valid, is_whisper_lock, load_model_with_loading_screen, unload_stt_model, get_model_from_settings, WhisperModelStatus, get_whisper_model, set_whisper_model
from services.factual_consistency import find_factual_inconsistency
import utils.arg_parser
from services.whisper_hallucination_cleaner import hallucination_cleaner, load_hallucination_cleaner_model
from utils.log_config import logger
from UI.NoteStyleSelector import NoteStyleSelector
from utils.network.base import NetworkConfig
from utils.network.openai_client import OpenAIClient

# parse command line arguments
utils.arg_parser.parse_args()

APP_NAME = 'AI Medical Scribe'  # Application name
if utils.system.is_windows():
    APP_TASK_MANAGER_NAME = 'freescribe-client.exe'
else:
    APP_TASK_MANAGER_NAME = 'FreeScribe'

logger.info(f"{APP_NAME=} {APP_TASK_MANAGER_NAME=} {get_application_version()=}")

# check if another instance of the application is already running.
# if false, create a new instance of the application
# if true, exit the current instance
app_manager = OneInstance(APP_NAME, APP_TASK_MANAGER_NAME)

if app_manager.is_running():
    # Another instance is running
    sys.exit(1)
else:
    # No other instance is running, or we successfully terminated the other instance
    root = tk.Tk()
    root.title(APP_NAME)

if utils.system.is_macos():
    utils.system.install_macos_ssl_certificates()


def delete_temp_file(filename):
    """
    Deletes a temporary file if it exists.

    Args:
        filename (str): The name of the file to delete.
    """
    file_path = get_resource_path(filename)
    if os.path.exists(file_path):
        try:
            logger.info(f"Deleting temporary file: {filename}")
            os.remove(file_path)
        except OSError as e:
            logger.exception(f"Error deleting temporary file {filename}: {e}")

def on_closing():
    delete_temp_file('recording.wav')
    delete_temp_file('realtime.wav')

    #save all notes
    save_notes_history()
     
    # Cancel any pending async operations
    try:
        loop = asyncio.get_running_loop()
        if loop and not loop.is_closed():
            # Cancel all pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
    except RuntimeError as e:
        logger.exception(f"Error during async cleanup: {e}")
        pass  # No running loop

    app_manager.cleanup()


# Register the cleanup function to be called on exit
atexit.register(on_closing)

def enable_notes_history(event=None):
    """
    Enables the 'Store Notes Locally' setting in the application settings.
    """
    load_notes_history()
    warning_label.grid_remove()
    grid_clear_all_btn()

root.bind("<<EnableNoteHistory>>", enable_notes_history)

def disable_notes_history(event=None):
    """
    Disables the 'Store Notes Locally' setting in the application settings.
    Clears all existing notes and updates the UI accordingly.
    """
    clear_all_notes()
    clear_all_notes_btn.grid_remove()
    grid_warning_label()

root.bind("<<DisableNoteHistory>>", disable_notes_history)

def load_notes_history():
    """
    Loads the temporary notes from a local .txt file containing encrypted JSON data and populates the response_history list.
    """
    #ensure the box is empty
    root.after(0, lambda: timestamp_listbox.delete(0, tk.END))  # Clear the timestamp listbox

    notes_file_path = get_resource_path('notes_history.txt')
    try:
        with open(notes_file_path, 'r') as file:
            encrypted_data = file.read()
        
        # Decrypt the JSON data
        json_data = AESCryptoUtils.AESCryptoUtilsClass.decrypt(encrypted_data)

        notes_data = json.loads(json_data)
        for entry in notes_data:
            timestamp = entry["timestamp"]
            user_message = entry["user_message"]
            response_text = entry["response_text"]
            response_history.append((timestamp, user_message, response_text))
        populate_ui_with_notes()
        logger.info(f"Temporary notes loaded from {notes_file_path}")
    except FileNotFoundError:
        logger.info(f"No temporary notes file found at {notes_file_path}")
    except Exception as e:
        logger.exception(f"Error loading temporary notes: {e}")

def populate_ui_with_notes():
    """
    Populates the UI components with the data from response_history.
    """
    def action():
        global IS_FIRST_LOG
        IS_FIRST_LOG = False
        
        timestamp_listbox.delete(0, tk.END)
        for time, user_msg, response in response_history:
            timestamp_listbox.insert(tk.END, time)

    root.after(0, action)

def clear_all_notes():
    """
    Clears all temporary notes from the UI and the .txt file.
    """
    global response_history
    response_history = []  # Clear the response history list

    clear_notes_ui_element()  # Clear the UI elements

    # Clear the contents of the .txt file
    notes_file_path = get_resource_path('notes_history.txt')
    try:
        with open(notes_file_path, 'w') as file:
            file.write("")  # Write an empty string to clear the file
        logger.info(f"Temporary notes file cleared: {notes_file_path}")
    except Exception as e:
        logger.exception(f"Error clearing temporary notes file: {e}")

def clear_notes_ui_element():
    """Clears the UI elements displaying the notes."""
    # Clear the timestamp listbox
    def action():
        timestamp_listbox.delete(0, tk.END)

        # Clear the response display
        response_display.scrolled_text.configure(state='normal')
        response_display.scrolled_text.delete("1.0", tk.END)
        response_display.scrolled_text.insert(tk.END, "Medical Note")

    root.after(0, action)

def safe_set_button_config(button, **kwargs):
    """
    Safely sets configuration options for a button in the UI.

    Args:
        button (tk.Button): The button to update.
        **kwargs: Arbitrary keyword arguments for button configuration options (e.g., text, state, etc.).
    """
    def update_text(button, **kwargs):
        if button.winfo_exists():
            button.config(**kwargs)
        else:
            logger.warning("Button does not exist, cannot set text.")
    root.after(0, lambda: update_text(button, **kwargs))

def safe_set_transcription_box(text, callback=None):
    """
    Safely sets the text of the transcription box in the UI.

    Args:
        text (str): The text to set on the transcription box.
        callback (callable, optional): Function to call after text is updated.
    """
    def update_text():
        if user_input.scrolled_text.winfo_exists():
            user_input.scrolled_text.configure(state='normal')
            user_input.scrolled_text.delete("1.0", tk.END)
            user_input.scrolled_text.insert(tk.END, text)
            if callback:
                callback()
        else:
            logger.warning("Transcription box does not exist, cannot set text.")
    root.after(0, update_text)

def safe_set_note_box(text):
    """
    Safely sets the text of the note box in the UI.

    Args:
        text (str): The text to set on the note box.
    """
    def update_text():
        if response_display.scrolled_text.winfo_exists():
            response_display.scrolled_text.configure(state='normal')
            response_display.scrolled_text.delete("1.0", tk.END)
            response_display.scrolled_text.insert(tk.END, text)
        else:
            logger.warning("Note box does not exist, cannot set text.")
    root.after(0, update_text)

# This runs before on_closing, if not confirmed, nothing should be changed
def confirm_exit_and_destroy():
    """Show confirmation dialog before exiting the application.

    Displays a warning message about temporary note history being cleared on exit.
    If the user confirms, triggers the window close event. If canceled, the application
    remains open.

    .. note::
        This function is bound to the window's close button (WM_DELETE_WINDOW protocol).

    .. warning::
        All temporary note history will be permanently cleared when the application closes.

    :returns: None
    :rtype: None
    """
    if messagebox.askokcancel(
            "Confirm Exit",
            "Warning: Temporary Note History will be cleared when app closes.\n\n"
            "Please make sure you have copied your important notes elsewhere "
            "before closing.\n\n"
            "Do you still want to exit?"
    ):
        root.destroy()


# remind user notes will be gone after exiting
root.protocol("WM_DELETE_WINDOW", confirm_exit_and_destroy)

# settings logic
app_settings = SettingsWindow()

if app_settings.editable_settings[SettingsKeys.ENABLE_FILE_LOGGER.value]:
    utils.log_config.add_file_handler(utils.log_config.logger, format=utils.log_config.AESEncryptedFormatter())

#  create our ui elements and settings config
window = MainWindowUI(root, app_settings)

app_settings.set_main_window(window)

if app_settings.editable_settings["Use Docker Status Bar"]:
    window.create_docker_status_bar()

NOTE_CREATION = "Note Creation...Please Wait"

user_message = []
response_history = []
current_view = "full"
username = "user"
botname = "Assistant"
num_lines_to_keep = 20
uploaded_file_path = None
is_recording = False
recording_thread = None
is_realtimeactive = False
audio_data = []
frames = []
is_paused = False
is_flashing = False
use_aiscribe = True
is_gpt_button_active = False
p = pyaudio.PyAudio()
audio_queue = queue.Queue()
CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
silent_warning_duration = 0

# Application flags
is_audio_processing_realtime_canceled = threading.Event()
is_audio_processing_whole_canceled = threading.Event()
cancel_await_thread = threading.Event()


# Constants
if utils.system.is_linux():
    DEFAULT_BUTTON_COLOUR = "grey85"
else:
    DEFAULT_BUTTON_COLOUR = "SystemButtonFace"

# Thread tracking variables
REALTIME_TRANSCRIBE_THREAD_ID = None
GENERATION_THREAD_ID = None


def get_prompt(formatted_message):

    sampler_order = app_settings.editable_settings["sampler_order"]
    if isinstance(sampler_order, str):
        sampler_order = json.loads(sampler_order)
    return {
        "prompt": f"{formatted_message}\n",
        "use_story": app_settings.editable_settings["use_story"],
        "use_memory": app_settings.editable_settings["use_memory"],
        "use_authors_note": app_settings.editable_settings["use_authors_note"],
        "use_world_info": app_settings.editable_settings["use_world_info"],
        "max_context_length": int(app_settings.editable_settings["max_context_length"]),
        "max_length": int(app_settings.editable_settings["max_length"]),
        "rep_pen": float(app_settings.editable_settings["rep_pen"]),
        "rep_pen_range": int(app_settings.editable_settings["rep_pen_range"]),
        "rep_pen_slope": float(app_settings.editable_settings["rep_pen_slope"]),
        "temperature": float(app_settings.editable_settings["temperature"]),
        "tfs": float(app_settings.editable_settings["tfs"]),
        "top_a": float(app_settings.editable_settings["top_a"]),
        "top_k": int(app_settings.editable_settings["top_k"]),
        "top_p": float(app_settings.editable_settings["top_p"]),
        "typical": float(app_settings.editable_settings["typical"]),
        "sampler_order": sampler_order,
        "singleline": app_settings.editable_settings["singleline"],
        "frmttriminc": app_settings.editable_settings["frmttriminc"],
        "frmtrmblln": app_settings.editable_settings["frmtrmblln"]
    }


def threaded_check_stt_model():
    """
    Starts a new thread to check the status of the speech-to-text (STT) model loading process.

    A separate thread is spawned to run the `double_check_stt_model_loading` function,
    which monitors the loading of the STT model. The function waits for the task to be completed and
    handles cancellation if requested.
    """
    # Create a Boolean variable to track if the task is done/canceled
    task_done_var = tk.BooleanVar(value=False)
    task_cancel_var = tk.BooleanVar(value=False)

    # Start a new thread to run the double_check_stt_model_loading function
    stt_thread = threading.Thread(target=double_check_stt_model_loading, args=(task_done_var, task_cancel_var))
    stt_thread.start()

    # Wait for the task_done_var to be set to True (indicating task completion)
    root.wait_variable(task_done_var)

    # Check if the task was canceled via task_cancel_var
    if task_cancel_var.get():
        logger.debug("double checking canceled")
        return False
    return True


def threaded_toggle_recording(button):
    # quick fix: prevents the button being clicked repeatedly in short time, avoid UI freeze
    button.config(state="disabled")
    root.after(1000, lambda: button.config(state="normal"))

    ready_flag = threaded_check_stt_model()
    # there is no point start recording if we are using local STT model and it's not ready
    # if user chooses to cancel the double check process, we need to return and not start recording
    if not ready_flag:
        return
    thread = threading.Thread(target=toggle_recording)
    thread.start()


def double_check_stt_model_loading(task_done_var, task_cancel_var):
    logger.info(f"*** Double Checking STT model - Model Current Status: {is_whisper_valid()}")
    stt_loading_window = None
    try:
        if is_recording:
            logger.info("*** Recording in progress, skipping double check")
            return
        if not app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]:
            logger.info("*** Local Whisper is disabled, skipping double check")
            return
        if is_whisper_valid():
            logger.info("*** STT model already loaded, skipping double check")
            return
        # if using local whisper and model is not loaded, when starting recording
        if is_whisper_lock():
            model_name = app_settings.editable_settings[SettingsKeys.WHISPER_MODEL.value].strip()
            stt_loading_window = LoadingWindow(root, "Loading Speech to Text model",
                                               f"Loading {model_name} model. Please wait.",
                                               on_cancel=lambda: task_cancel_var.set(True))
            timeout = 300
            time_start = time.monotonic()
            # wait until the other loading thread is done
            while True:
                time.sleep(0.1)
                if task_cancel_var.get():
                    # user cancel
                    logger.debug(f"user canceled after {time.monotonic() - time_start} seconds")
                    return
                if time.monotonic() - time_start > timeout:
                    messagebox.showerror("Error",
                                         f"Timed out while loading local Speech to Text model after {timeout} seconds.")
                    task_cancel_var.set(True)
                    return
                if not is_whisper_lock():
                    break
            stt_loading_window.destroy()
            stt_loading_window = None
        # double check
        if is_whisper_valid():
            # mandatory loading, synchronous
            t = load_model_with_loading_screen(root=root, app_settings=app_settings)
            t.join()

    except Exception as e:
        logger.exception(str(e))
        messagebox.showerror("Error",
                             f"An error occurred while loading Speech to Text model synchronously {type(e).__name__}: {e}")
    finally:
        logger.info(f"*** Double Checking STT model Complete - Model Current Status: {is_whisper_valid()}")
        if stt_loading_window:
            stt_loading_window.destroy()
        task_done_var.set(True)


def threaded_realtime_text():
    thread = threading.Thread(target=realtime_text)
    thread.start()
    return thread


def threaded_handle_message(formatted_message):
    thread = threading.Thread(target=show_edit_transcription_popup, args=(formatted_message,))
    thread.start()
    return thread


def threaded_send_audio_to_server():
    thread = threading.Thread(target=send_audio_to_server)
    thread.start()
    return thread


def toggle_pause():
    def action():
        global is_paused
        is_paused = not is_paused

        if is_paused:
            if current_view == "full":
                pause_button.config(text="Resume", bg="red")
            elif current_view == "minimal":
                pause_button.config(text="▶️", bg="red")
        else:
            if current_view == "full":
                pause_button.config(text="Pause", bg=DEFAULT_BUTTON_COLOUR)
            elif current_view == "minimal":
                pause_button.config(text="⏸️", bg=DEFAULT_BUTTON_COLOUR)

    root.after(0, action)
    
SILENCE_WARNING_LENGTH = 10 # seconds, warn the user after 10s of no input something might be wrong

def open_microphone_stream():
    """
    Opens an audio stream from the selected microphone.

    This function retrieves the index of the selected microphone from the
    MicrophoneTestFrame and attempts to open an audio stream using the pyaudio
    library. If successful, it returns the stream object and None. In case of
    an error (either OSError or IOError), it logs the error message and returns
    None along with the error object.

    Returns:
        tuple: A tuple containing the stream object (or None if an error occurs)
               and the error object (or None if no error occurs).
    """

    try:
        selected_index = MicrophoneTestFrame.get_selected_microphone_index()
        stream = p.open(
            format=FORMAT,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=int(selected_index))

        return stream, None
    except (OSError, IOError) as e:
        # Log the error message
        # TODO System logger
        logger.exception(f"An error occurred opening the stream({type(e).__name__}): {e}")
        return None, e


def record_audio():
    """
    Records audio from the selected microphone, processes the audio to detect silence,
    and manages the recording state.

    Global Variables:
        is_paused (bool): Indicates whether the recording is paused.
        frames (list): List of audio data frames.
        audio_queue (queue.Queue): Queue to store recorded audio chunks.

    Returns:
        None: The function does not return a value. It interacts with global variables.
    """
    global is_paused, frames, audio_queue, silent_warning_duration

    try:
        recording_id = f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        current_chunk = []
        silent_duration = 0
        record_duration = 0
        minimum_silent_duration = float(app_settings.editable_settings["Real Time Silence Length"])
        minimum_audio_duration = float(app_settings.editable_settings["Real Time Audio Length"])

        stream, stream_exception = open_microphone_stream()

        if stream is None:
            clear_application_press()
            messagebox.showerror("Error", f"An error occurred while trying to record audio: {stream_exception}")
            logger.error(f"An error occurred while trying to record audio: {stream_exception}")
        
        audio_data_leng = 0
        while is_recording and stream is not None:
            if not is_paused:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                # Check for silence
                audio_buffer = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768

                # convert the setting from str to float
                try:
                    speech_prob_threshold = float(
                        app_settings.editable_settings[SettingsKeys.SILERO_SPEECH_THRESHOLD.value])
                except ValueError:
                    # default it to value in DEFAULT_SETTINGS_TABLE on invalid error
                    speech_prob_threshold = app_settings.DEFAULT_SETTINGS_TABLE[SettingsKeys.SILERO_SPEECH_THRESHOLD.value]
                    logger.info(f"Invalid value for SILERO_SPEECH_THRESHOLD: {app_settings.editable_settings[SettingsKeys.SILERO_SPEECH_THRESHOLD.value]}. Defaulting to {speech_prob_threshold}")

                if is_silent(audio_buffer, speech_prob_threshold ):
                    silent_duration += CHUNK / RATE
                    silent_warning_duration += CHUNK / RATE
                else:
                    silent_duration = 0
                    silent_warning_duration = 0
                    audio_data_leng += CHUNK / RATE

                current_chunk.append(data)
                
                record_duration += CHUNK / RATE

                # Check if we need to warn if silence is long than warn time
                root.after(0, lambda: check_silence_warning(silent_warning_duration))

                # 1 second of silence at the end so we dont cut off speech
                if silent_duration >= minimum_silent_duration and audio_data_leng > 1.5  and record_duration > minimum_audio_duration:
                    if app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value] and current_chunk:
                        padded_audio = utils.audio.pad_audio_chunk(current_chunk, pad_seconds=0.5)
                        audio_queue.put(b''.join(padded_audio))
                    
                    if app_settings.editable_settings[SettingsKeys.STORE_RECORDINGS_LOCALLY.value]:
                        # Encrypt the audio chunk and save it to a file
                        utils.audio.encrypt_audio_chunk(b''.join(current_chunk), filepath=recording_id)

                    # Carry over the last .1 seconds of audio to the next one so next speech does not start abruptly or in middle of a word
                    carry_over_chunk = current_chunk[-int(0.1 * RATE / CHUNK):]
                    current_chunk = [] 
                    current_chunk.extend(carry_over_chunk)

                    # reset the variables and state holders for realtime audio processing
                    audio_data_leng = 0
                    silent_duration = 0
                    record_duration = 0
            else:
                # Add a small delay to prevent high CPU usage
                time.sleep(0.01)


        # Send any remaining audio chunk when recording stops
        if current_chunk:
            last_chunk = b''.join(current_chunk)
            audio_queue.put(last_chunk)
            if app_settings.editable_settings[SettingsKeys.STORE_RECORDINGS_LOCALLY.value]:
                utils.audio.encrypt_audio_chunk(last_chunk, filepath=recording_id)
    except Exception as e:
        # Log the error message
        # TODO System logger
        # For now general catch on any problems
        logger.exception(f"An error occurred: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        audio_queue.put(None)

        # If the warning bar is displayed, remove it
        if window.warning_bar is not None:
            root.after(0, lambda: window.destroy_warning_bar())


def check_silence_warning(silence_duration):
    """Check if silence warning should be displayed."""

    # Check if we need to warn if silence is long than warn time
    if silence_duration >= SILENCE_WARNING_LENGTH and window.warning_bar is None and not is_paused:
        if current_view == "full":            
            window.create_warning_bar(f"No audio input detected for {SILENCE_WARNING_LENGTH} seconds. Please check and ensure your microphone input device is working.", closeButton=False)
        elif current_view == "minimal":
            window.create_warning_bar(f"🔇No audio for {SILENCE_WARNING_LENGTH}s.", closeButton=False)
    elif silence_duration <= SILENCE_WARNING_LENGTH and window.warning_bar is not None:
        # If the warning bar is displayed, remove it
        window.destroy_warning_bar()


silero, _silero = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')


def is_silent(data, threshold: float = 0.65):
    """Check if audio chunk contains speech using Silero VAD"""
    # Convert audio data to tensor and ensure correct format
    audio_tensor = torch.FloatTensor(data)
    if audio_tensor.dim() == 2:
        audio_tensor = audio_tensor.mean(dim=1)

    # Get speech probability
    speech_prob = silero(audio_tensor, 16000).item()
    return speech_prob < threshold


def realtime_text():
    global is_realtimeactive, audio_queue
    # Incase the user starts a new recording while this one the older thread is finishing.
    # This is a local flag to prevent the processing of the current audio chunk
    # if the global flag is reset on new recording
    local_cancel_flag = False
    if not is_realtimeactive:
        is_realtimeactive = True
        # this is the text that will be used to process intents
        intent_text = ""

        while True:
            #  break if canceled
            if is_audio_processing_realtime_canceled.is_set():
                local_cancel_flag = True
                break

            audio_data = audio_queue.get()
            if audio_data is None:
                break
            if app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value] == True:
                logger.info("Real Time Audio to Text")
                audio_buffer = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768
                if app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value] == True:
                    logger.info(f"Local Real Time Whisper {audio_queue.qsize()=}")
                    if not is_whisper_valid():

                        update_gui("Local Whisper model not loaded. Please check your settings.")
                        break
                    try:
                        result = faster_whisper_transcribe(audio_buffer, app_settings=app_settings)
                        if app_settings.editable_settings[SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value] and FeatureToggle.HALLUCINATION_CLEANING:
                            result = hallucination_cleaner.clean_text(result)
                    except Exception as e:
                        logger.exception(str(e))
                        update_gui(f"\nError: {e}\n")
                        logger.exception(f"Error: {e}")

                    if not local_cancel_flag and not is_audio_processing_realtime_canceled.is_set():
                        update_gui(result)
                        intent_text = result
                else:
                    logger.info("Remote Real Time Whisper")
                    buffer = io.BytesIO()
                    with wave.open(buffer, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(p.get_sample_size(FORMAT))
                        wf.setframerate(RATE)
                        wf.writeframes(audio_data)

                    buffer.seek(0)  # Reset buffer position

                    files = {'audio': buffer}

                    headers = {
                        "Authorization": f"Bearer {app_settings.editable_settings[SettingsKeys.WHISPER_SERVER_API_KEY.value]}"
                    }

                    body = {
                        "use_translate": app_settings.editable_settings[SettingsKeys.USE_TRANSLATE_TASK.value],
                    }

                    if app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value] not in SettingsWindow.AUTO_DETECT_LANGUAGE_CODES:
                        body["language_code"] = app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value]

                    if app_settings.editable_settings[SettingsKeys.WHISPER_INITIAL_PROMPT.value].strip() not in SettingsWindow.AUTO_DETECT_LANGUAGE_CODES:
                        body['initial_prompt'] = app_settings.editable_settings[SettingsKeys.WHISPER_INITIAL_PROMPT.value].strip()

                    try:
                        verify = not app_settings.editable_settings[SettingsKeys.S2T_SELF_SIGNED_CERT.value]

                        logger.info("Sending audio to server")
                        logger.info("File informaton")
                        logger.info(f"File Size: {len(buffer.getbuffer())} bytes")

                        response = requests.post(app_settings.editable_settings[SettingsKeys.WHISPER_ENDPOINT.value], headers=headers,files=files, verify=verify, data=body)
                            
                        logger.info(f"Response from whisper with status code: {response.status_code}")

                        if response.status_code == 200:
                            text = response.json()['text']
                            if app_settings.editable_settings[SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value] and FeatureToggle.HALLUCINATION_CLEANING:
                                text = hallucination_cleaner.clean_text(text)
                            if not local_cancel_flag and not is_audio_processing_realtime_canceled.is_set():
                                update_gui(text)
                                intent_text = text
                        else:
                            update_gui(f"Error (HTTP Status {response.status_code}): {response.text}")
                    except Exception as e:
                        update_gui(f"Error: {e}")
                        logger.exception(f"Error: {e}")
                    finally:
                        # close buffer. we dont need it anymore
                        buffer.close()
                # Process intents
                if FeatureToggle.INTENT_ACTION:
                    try:
                        logger.debug(f"Processing intents for text: {intent_text}")
                        window.get_text_intents(intent_text)
                    except Exception as e:
                        logger.exception(f"Error processing intents: {e}")
            audio_queue.task_done()

        # unload thestt model on low mem mode
        if app_settings.is_low_mem_mode():
            unload_stt_model()  
    else:
        is_realtimeactive = False


def update_gui(text):
    def action(text):
        if user_input.scrolled_text.winfo_exists():
            user_input.scrolled_text.configure(state='normal')  # enable for editing
            user_input.scrolled_text.insert(tk.END, text + '\n')
            user_input.scrolled_text.see(tk.END)
    root.after(0, lambda: action(text))

def save_audio():
    global frames
    if frames:
        with wave.open(get_resource_path("recording.wav"), 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        frames = []  # Clear recorded data

    if app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value] == True and is_audio_processing_realtime_canceled.is_set(
    ) is False:
        send_and_receive()
    elif app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value] == False and is_audio_processing_whole_canceled.is_set() is False:
        threaded_send_audio_to_server()


def toggle_recording():
    global is_recording, recording_thread, DEFAULT_BUTTON_COLOUR, audio_queue, current_view, REALTIME_TRANSCRIBE_THREAD_ID, frames, silent_warning_duration

    # Reset the cancel flags going into a fresh recording
    if not is_recording:
        is_audio_processing_realtime_canceled.clear()
        is_audio_processing_whole_canceled.clear()

    if is_paused:
        toggle_pause()

    realtime_thread = threaded_realtime_text()

    if not is_recording:
        #load the stt model for transcription
        if not is_whisper_valid() and app_settings.is_low_mem_mode():
            loading_screen = LoadingWindow(root, "Loading Speech to Text model", "Loading Speech to Text model. Please wait.")
            load_stt_model(app_settings=app_settings)
            loading_screen.destroy()
            
        disable_recording_ui_elements()
        # reset generate button state
        safe_set_button_config(send_button, text="Generate Note", bg=DEFAULT_BUTTON_COLOUR, state='normal')
        safe_set_transcription_box("")

        REALTIME_TRANSCRIBE_THREAD_ID = realtime_thread.ident
        
        if not app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value]:
            safe_set_transcription_box("Recording Audio... Realtime Transcription disabled. Audio while transcribe when you press stop recording.\n")
      
        # Set the text in the transcription box, nothing for it to be empty
        safe_set_note_box("")

        is_recording = True

        # reset frames before new recording so old data is not used
        frames = []
        silent_warning_duration = 0
        recording_thread = threading.Thread(target=record_audio)
        recording_thread.start()

        if current_view == "full":
            safe_set_button_config(mic_button, bg="red", text="Stop\nRecording")
        elif current_view == "minimal":
            safe_set_button_config(mic_button, bg="red", text="⏹️")

        start_flashing()
    else:
        enable_recording_ui_elements()
        if current_view == "full":
            safe_set_button_config(mic_button, bg=DEFAULT_BUTTON_COLOUR, text="Start\nRecording")
        elif current_view == "minimal":
            safe_set_button_config(mic_button, bg=DEFAULT_BUTTON_COLOUR, text="🎤")
        is_recording = False
        if recording_thread and recording_thread.is_alive():
            recording_thread.join()  # Ensure the recording thread is terminated

        if app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value] and not is_audio_processing_realtime_canceled.is_set(
        ):
            def cancel_realtime_processing(thread_id):
                """Cancels any ongoing audio processing.

                Sets the global flag to stop audio processing operations.
                """
                global REALTIME_TRANSCRIBE_THREAD_ID

                try:
                    kill_thread(thread_id)
                except Exception as e:
                    logger.exception(f"An error occurred: {e}")
                finally:
                    REALTIME_TRANSCRIBE_THREAD_ID = None

                # empty the queue
                while not audio_queue.empty():
                    audio_queue.get()
                    audio_queue.task_done()

            loading_window = LoadingWindow(
                root,
                "Processing Audio",
                "Processing Audio. Please wait.",
                on_cancel=lambda: (
                    cancel_processing(),
                    cancel_realtime_processing(REALTIME_TRANSCRIBE_THREAD_ID)))

            try:
                timeout_length = int(app_settings.editable_settings[SettingsKeys.AUDIO_PROCESSING_TIMEOUT_LENGTH.value])
            except ValueError:
                # default to 3minutes
                timeout_length = 180
                logger.info(f"Invalid value for AUDIO_PROCESSING_TIMEOUT_LENGTH: {app_settings.editable_settings[SettingsKeys.AUDIO_PROCESSING_TIMEOUT_LENGTH.value]}. Defaulting to {timeout_length} seconds")

            timeout_timer = 0.0
            while audio_queue.empty() is False and timeout_timer < timeout_length:
                # break because cancel was requested
                if is_audio_processing_realtime_canceled.is_set():
                    break
                # increment timer
                timeout_timer += 0.1
                # round to 10 decimal places, account for floating point errors
                timeout_timer = round(timeout_timer, 10)

                # check if we should print a message every 5 seconds
                if timeout_timer % 5 == 0:
                    logger.info(f"Waiting for audio processing to finish. Timeout after {timeout_length} seconds. Timer: {timeout_timer}s")

                # Wait for 100ms before checking again, to avoid busy waiting
                time.sleep(0.1)

            loading_window.destroy()

            realtime_thread.join()

        save_audio()

        logger.info("*** Recording Stopped")
        stop_flashing()

def disable_recording_ui_elements():
    def action():
        window.disable_settings_menu()
        user_input.scrolled_text.configure(state='disabled')
        send_button.config(state='disabled')
        #hidding the AI Scribe button actions
        #toggle_button.config(state='disabled')
        upload_button.config(state='disabled')
        response_display.scrolled_text.configure(state='disabled')
        timestamp_listbox.config(state='disabled')
        clear_button.config(state='disabled')
        mic_test.set_mic_test_state(False)
    root.after(0, action)

def enable_recording_ui_elements():
    def action():
        window.enable_settings_menu()
        user_input.scrolled_text.configure(state='normal')
        send_button.config(state='normal')
        #hidding the AI Scribe button actions
        #toggle_button.config(state='normal')
        upload_button.config(state='normal')
        timestamp_listbox.config(state='normal')
        clear_button.config(state='normal')
        mic_test.set_mic_test_state(True)

    root.after(0, action)
        

def cancel_processing():
    """Cancels any ongoing audio processing.

    Sets the global flag to stop audio processing operations.
    """
    logger.info("Processing canceled.")

    if app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value]:
        is_audio_processing_realtime_canceled.set()  # Flag to terminate processing
    else:
        is_audio_processing_whole_canceled.set()  # Flag to terminate processing


def clear_application_press():
    """Resets the application state by clearing text fields and recording status."""
    reset_recording_status()  # Reset recording-related variables
    clear_all_text_fields()  # Clear UI text areas
    # change re generate button to generate button
    safe_set_button_config(send_button, text="Generate Note", bg=DEFAULT_BUTTON_COLOUR, state='normal')


def reset_recording_status():
    """Resets all recording-related variables and stops any active recording.

    Handles cleanup of recording state by:
        - Checking if recording is active
        - Canceling any processing
        - Stopping the recording thread
    """
    global is_recording, frames, audio_queue, REALTIME_TRANSCRIBE_THREAD_ID, GENERATION_THREAD_ID
    if is_recording:  # Only reset if currently recording
        cancel_processing()  # Stop any ongoing processing
        threaded_toggle_recording()  # Stop the recording thread

    # kill the generation thread if active
    if REALTIME_TRANSCRIBE_THREAD_ID:
        # Exit the current realtime thread
        try:
            kill_thread(REALTIME_TRANSCRIBE_THREAD_ID)
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
        finally:
            REALTIME_TRANSCRIBE_THREAD_ID = None

    if GENERATION_THREAD_ID:
        try:
            kill_thread(GENERATION_THREAD_ID)
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
        finally:
            GENERATION_THREAD_ID = None


def clear_all_text_fields():
    """Clears and resets all text fields in the application UI.

    Performs the following:
        - Clears user input field
        - Resets focus
        - Stops any flashing effects
        - Resets response display with default text
    """
    # Enable and clear user input field
    safe_set_transcription_box("")
    
    # Reset focus to main window
    def set_focus():
        user_input.scrolled_text.focus_set()
        root.focus_set()

    root.after(0, set_focus)  # Use after to ensure focus is set after UI updates
    

    stop_flashing()  # Stop any UI flashing effects

    # Reset response display with default text
    safe_set_note_box("Medical Note")

# hidding the AI Scribe button Function
# def toggle_aiscribe():
#     global use_aiscribe
#     use_aiscribe = not use_aiscribe
#     toggle_button.config(text="AI Scribe\nON" if use_aiscribe else "AI Scribe\nOFF")


def send_audio_to_server():
    """
    Sends an audio file to either a local or remote Whisper server for transcription.

    Global Variables:
    ----------------
    uploaded_file_path : str
        The path to the uploaded audio file. If `None`, the function defaults to
        'recording.wav'.

    Parameters:
    -----------
    None

    Returns:
    --------
    None

    Raises:
    -------
    ValueError
        If the `app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]` flag is not a boolean.
    FileNotFoundError
        If the specified audio file does not exist.
    requests.exceptions.RequestException
        If there is an issue with the HTTP request to the remote server.
    """

    global uploaded_file_path
    current_thread_id = threading.current_thread().ident

    def cancel_whole_audio_process(thread_id):
        global GENERATION_THREAD_ID

        is_audio_processing_whole_canceled.clear()

        try:
            kill_thread(thread_id)
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
        finally:
            GENERATION_THREAD_ID = None
            clear_application_press()
            stop_flashing()

    loading_window = LoadingWindow(
        root,
        "Processing Audio",
        "Processing Audio. Please wait.",
        on_cancel=lambda: (
            cancel_processing(),
            cancel_whole_audio_process(current_thread_id)))

    # Check if SettingsKeys.LOCAL_WHISPER is enabled in the editable settings
    if app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value] == True:
        # Inform the user that SettingsKeys.LOCAL_WHISPER.value is being used for transcription
        logger.info(f"Using {SettingsKeys.LOCAL_WHISPER.value} for transcription.")

        clear_all_text_fields()

        # Configure the user input widget to be editable and clear its content
        safe_set_transcription_box("Audio to Text Processing...Please Wait")
        try:
            if utils.system.is_macos():
                # Load the audio file to send for transcription
                file_to_send, sr = librosa.load(uploaded_file_path, sr=RATE, mono=True)
                delete_file = False
                uploaded_file_path = None
            else:
                # Determine the file to send for transcription
                file_to_send = uploaded_file_path or get_resource_path('recording.wav')
                delete_file = False if uploaded_file_path else True
                uploaded_file_path = None


            # load stt model for transcription
            if not is_whisper_valid() and app_settings.is_low_mem_mode():
                model_id = get_model_from_settings(app_settings=app_settings)
                model_load_window = LoadingWindow(root, 
                title = "Speech to Text model", 
                initial_text = f"Loading Speech to Text model({model_id}). Please wait.")
                load_thread = load_stt_model(app_settings=app_settings)
                load_thread.join()
                model_load_window.destroy()

            # Transcribe the audio file using the loaded model
            try:
                result = faster_whisper_transcribe(file_to_send, app_settings=app_settings)
                if app_settings.editable_settings[SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value] and FeatureToggle.HALLUCINATION_CLEANING:
                    result = hallucination_cleaner.clean_text(result)
            except Exception as e:
                result = f"An error occurred ({type(e).__name__}): {e}\n \n {traceback.format_exc()}"
                logger.exception(f"An error occurred: {e}")
            finally:
                if app_settings.is_low_mem_mode():
                    unload_stt_model()

            transcribed_text = result

            # done with file clean up
            if delete_file is True and os.path.exists(file_to_send) :
                os.remove(file_to_send)

            # check if canceled, if so do not update the UI
            if not is_audio_processing_whole_canceled.is_set():
                safe_set_transcription_box(transcribed_text, send_and_receive)
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
            safe_set_transcription_box(f"An error occurred: {e}")
        finally:
            loading_window.destroy()

    else:
        # Inform the user that Remote Whisper is being used for transcription
        logger.info("Using Remote Whisper for transcription.")

        # Configure the user input widget to be editable and clear its content
        safe_set_transcription_box("Audio to Text Processing...Please Wait")

        delete_file = False if uploaded_file_path else True

        # Determine the file to send for transcription
        if uploaded_file_path:
            file_to_send = uploaded_file_path
            uploaded_file_path = None
        else:
            file_to_send = get_resource_path('recording.wav')

        # Open the audio file in binary mode
        with open(file_to_send, 'rb') as f:
            files = {'audio': f}

            # Add the Bearer token to the headers for authentication
            headers = {
                "Authorization": f"Bearer {app_settings.editable_settings[SettingsKeys.WHISPER_SERVER_API_KEY.value]}"
            }

            body = {
                "use_translate": app_settings.editable_settings[SettingsKeys.USE_TRANSLATE_TASK.value],
            }

            if app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value] not in SettingsWindow.AUTO_DETECT_LANGUAGE_CODES:
                body["language_code"] = app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value]

            if app_settings.editable_settings[SettingsKeys.WHISPER_INITIAL_PROMPT.value] not in SettingsWindow.AUTO_DETECT_LANGUAGE_CODES:
                body['initial_prompt'] = app_settings.editable_settings[SettingsKeys.WHISPER_INITIAL_PROMPT.value]

            try:
                verify = not app_settings.editable_settings[SettingsKeys.S2T_SELF_SIGNED_CERT.value]

                logger.info("Sending audio to server")
                logger.info("File informaton")
                logger.info(f"File: {file_to_send}")
                logger.info(f"File Size: {os.path.getsize(file_to_send)}")

                # Send the request without verifying the SSL certificate
                response = requests.post(
                    app_settings.editable_settings[SettingsKeys.WHISPER_ENDPOINT.value], headers=headers, files=files, verify=verify, data=body)

                logger.info(f"Response from whisper with status code: {response.status_code}")

                response.raise_for_status()

                # check if canceled, if so do not update the UI
                if not is_audio_processing_whole_canceled.is_set():
                    # Update the UI with the transcribed text
                    transcribed_text = response.json()['text']
                    if app_settings.editable_settings[SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value] and FeatureToggle.HALLUCINATION_CLEANING:
                        transcribed_text = hallucination_cleaner.clean_text(transcribed_text)
                        try:
                            transcribed_text = hallucination_cleaner.clean_text(transcribed_text)
                            logger.debug(f"remote Cleaned result: {transcribed_text}")
                        except Exception as e:
                            # ignore the error as it should not break the transcription
                            logger.exception(f"remote Error during hallucination cleaning: {str(e)}")
                    safe_set_transcription_box(transcribed_text, send_and_receive)
            except Exception as e:
                logger.exception(f"An error occurred: {e}")
                # Display an error message to the user
                safe_set_transcription_box(f"An error occurred: {e}")
            finally:
                # done with file clean up
                f.close()
                if os.path.exists(file_to_send) and delete_file:
                    os.remove(file_to_send)
                loading_window.destroy()
    stop_flashing()


def kill_thread(thread_id):
    """
    Terminate a thread with a given thread ID.

    This function forcibly terminates a thread by raising a `SystemExit` exception in its context.
    **Use with caution**, as this method is not safe and can lead to unpredictable behavior,
    including corruption of shared resources or deadlocks.

    :param thread_id: The ID of the thread to terminate.
    :type thread_id: int
    :raises ValueError: If the thread ID is invalid.
    :raises SystemError: If the operation fails due to an unexpected state.
    """
    logger.info(f"*** Attempting to kill thread with ID: {thread_id}")
    # Call the C function `PyThreadState_SetAsyncExc` to asynchronously raise
    # an exception in the target thread's context.
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread_id),  # The thread ID to target (converted to `long`).
        ctypes.py_object(SystemExit)  # The exception to raise in the thread.
    )

    # Check the result of the function call.
    if res == 0:
        # If 0 is returned, the thread ID is invalid.
        raise ValueError(f"Invalid thread ID: {thread_id}")
    elif res > 1:
        # If more than one thread was affected, something went wrong.
        # Reset the state to prevent corrupting other threads.
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")
    logger.info(f"*** Killed thread with ID: {thread_id}")


def send_and_receive():
    global use_aiscribe, user_message
    user_message = user_input.scrolled_text.get("1.0", tk.END).strip()
    safe_set_note_box(NOTE_CREATION)
    threaded_handle_message(user_message)

def save_notes_history():
    """
    Saves the temporary notes to a local .txt file in encrypted JSON format.
    """
    notes_file_path = get_resource_path('notes_history.txt')
    try:
        # Convert response_history to a list of dictionaries
        notes_data = [
            {"timestamp": timestamp, "user_message": user_message, "response_text": response_text}
            for timestamp, user_message, response_text in response_history
        ]
        json_data = json.dumps(notes_data, indent=4)
        
        # Encrypt the JSON data
        encrypted_data = AESCryptoUtils.AESCryptoUtilsClass.encrypt(json_data)
        
        with open(notes_file_path, 'w') as file:
            file.write(encrypted_data)
        logger.info(f"Temporary notes saved to {notes_file_path}")
    except Exception as e:
        logger.exception(f"Error saving temporary notes: {e}")

def display_text(text):
    def _display_text():
        response_display.scrolled_text.configure(state='normal')
        response_display.scrolled_text.delete("1.0", tk.END)
        response_display.scrolled_text.insert(tk.END, f"{text}\n")
        response_display.scrolled_text.configure(state='disabled')
    root.after(0, _display_text)


IS_FIRST_LOG = True


def update_gui_with_response(response_text):
    def action(text):
        global response_history, user_message, IS_FIRST_LOG

        if IS_FIRST_LOG:
            timestamp_listbox.delete(0, tk.END)
            IS_FIRST_LOG = False

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response_history.insert(0, (timestamp, user_message, response_text))
        if app_settings.editable_settings[SettingsKeys.STORE_NOTES_LOCALLY.value]:
            save_notes_history()

        # Update the timestamp listbox
        timestamp_listbox.delete(0, tk.END)
        for time, _, _ in response_history:
            timestamp_listbox.insert(tk.END, time)

        safe_set_note_box(response_text)
        try:
            # copy/paste may be disabled in sandbox environment
            pyperclip.copy(response_text)
        except Exception as e:
            logger.warning(str(e))
    stop_flashing()
    
    root.after(0, lambda: action(response_text))


def show_response(event):
    global IS_FIRST_LOG

    if IS_FIRST_LOG:
        return

    selection = event.widget.curselection()
    if selection:
        index = selection[0]
        # set the regenerate note button
        safe_set_button_config(send_button, text="Regenerate Note", bg=DEFAULT_BUTTON_COLOUR, state='normal')
        transcript_text = response_history[index][1]
        response_text = response_history[index][2]
        safe_set_transcription_box(transcript_text)
        safe_set_note_box(response_text)

        try:
            pyperclip.copy(response_text)
        except Exception as e:
            logger.warning(str(e))

def send_text_to_api(edited_text, cancel_event):
    """
    Sends text to API using httpx AsyncClient in a cancellable async format.
    
    Args:
        edited_text (str): The text to send to the API
        cancel_event (threading.Event): Event to signal cancellation
        
    Returns:
        str: The response text or 'Error' if cancelled/failed
    """
    network_config = NetworkConfig(
        host=app_settings.editable_settings[SettingsKeys.LLM_ENDPOINT.value],
        api_key=app_settings.OPENAI_API_KEY,
        verify_ssl=not app_settings.editable_settings["AI Server Self-Signed Certificates"],
        timeout=180.0,  # Set a reasonable timeout for the request
        connect_timeout=10.0,
    )

    llm_client = OpenAIClient(config=network_config)

    generated_response = llm_client.send_chat_completion_sync(
        text=edited_text,
        model=app_settings.editable_settings[SettingsKeys.LOCAL_LLM_MODEL.value],
        threading_cancel_event=cancel_event,
        temperature=float(app_settings.editable_settings["temperature"]),
        top_p=float(app_settings.editable_settings["top_p"]),
        top_k=int(app_settings.editable_settings["top_k"]),
        stream=False,
    )

    return generated_response
         
def send_text_to_localmodel(edited_text):  
    # Send prompt to local model and get response
    if ModelManager.local_model is None:
        ModelManager.setup_model(app_settings=app_settings, root=root)

        timer = 0
        while ModelManager.local_model is None and timer < 30:
            timer += 0.1
            time.sleep(0.1)
       
    response  = ModelManager.local_model.generate_response(
        edited_text,
        temperature=float(app_settings.editable_settings["temperature"]),
        top_p=float(app_settings.editable_settings["top_p"]),
        repeat_penalty=float(app_settings.editable_settings["rep_pen"]),
    )

    if app_settings.is_low_mem_mode():
        ModelManager.unload_model()

    return response

def screen_input_with_llm(conversation):
    """
    Send a conversation to a large language model (LLM) for prescreening.
    :param conversation: A string containing the conversation to be screened.
    :return: A boolean indicating whether the conversation is valid.
    """
    # Define the chunk size (number of words per chunk)
    words_per_chunk = 60  # Adjust this value based on your results
    # Split the conversation into words
    words = conversation.split()
    # Split the words into chunks
    chunks = [' '.join(words[i:i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]
    logger.info(f"Total chunks count: {len(chunks)}")
    return any(process_chunk(chunk) for chunk in chunks)


def process_chunk(chunk):
    """
    Process a chunk of the conversation using the LLM.
    """
    prompt = (
        "Analyze the following conversation and determine if it is a valid doctor-patient conversation. "
        "A valid conversation involves a discussion between a healthcare provider and a patient about medical concerns, "
        "symptoms, diagnoses, treatments, or health management. It may include:\n"
        "- Descriptions of symptoms or health issues.\n"
        "- Discussions about medications, treatments, or follow-up plans.\n"
        "- Questions and answers related to the patient's health.\n"
        "- Casual or conversational tones, as long as the topic is medically relevant.\n\n"
        "If the conversation is unrelated to healthcare, lacks medical context, or appears to be non-medical, "
        "it is not a valid doctor-patient conversation.\n\n"
        "Return only one word: 'True' if the conversation is valid, or 'False' if it is not. "
        "Do not provide explanations, additional formatting, or any text other than 'True' or 'False'.\n\n"
        "Here is the conversation:\n"
    )
    # Send the prompt and chunk to the LLM for evaluation
    prescreen = send_text_to_chatgpt(f"{prompt}{chunk}")
    # Check if the response from the LLM is 'true' (case-insensitive)
    return prescreen.strip().lower() == "true"


def has_more_than_50_words(text: str) -> bool:
    # Split the text into words using whitespace as the delimiter
    words = text.split()
    # Print the number of words
    logger.info(f"Number of words: {len(words)}")
    # Check if the number of words is greater than 50
    return len(words) > 50


def display_screening_popup():
    """
    Display a popup window to inform the user of invalid input and offer options.

    :return: A boolean indicating the user's choice:
             - False if the user clicks 'Cancel'.
             - True if the user clicks 'Process Anyway!'.
    """
    # Create and display the popup window
    popup_result = PopupBox(
        parent=root,
        title="Invalid Input",
        message=(
            "Input has been flagged as invalid. Please ensure the input is a conversation with more than "
            "50 words between a doctor and a patient. Unexpected results may occur from the AI."
        ),
        button_text_1="Cancel",
        button_text_2="Process Anyway!"
    )

    # Return based on the button the user clicks
    if popup_result.response == "button_1":
        return False
    elif popup_result.response == "button_2":
        return True


def screen_input(user_message):
    """
    Screen the user's input message based on the application's settings.

    :param user_message: The message to be screened.
    :return: A boolean indicating whether the input is valid and accepted for further processing.
    """
    validators = []
    if app_settings.editable_settings[SettingsKeys.Enable_Word_Count_Validation.value]:
        validators.append(has_more_than_50_words)

    if app_settings.editable_settings[SettingsKeys.Enable_AI_Conversation_Validation.value]:
        validators.append(screen_input_with_llm)

    return all(validator(user_message) for validator in validators)


def threaded_screen_input(user_message, screen_return):
    """
    Screen the user's input message based on the application's settings in a separate thread.

    :param user_message: The message to be screened.
    :param screen_return: A boolean variable to store the result of the screening.
    """
    input_return = screen_input(user_message)
    screen_return.set(input_return)

def send_text_to_chatgpt(edited_text, cancel_event=None): 
    if app_settings.editable_settings[SettingsKeys.LOCAL_LLM.value]:
        return send_text_to_localmodel(edited_text)
    else:
        # send_text_to_api is already synchronous and handles async internally
        return send_text_to_api(edited_text, cancel_event)
    
def generate_note(formatted_message, cancel_event):
    """Generate a note from the formatted message.
    
    This function processes the input text and generates a medical note or AI response
    based on application settings. It supports pre-processing, post-processing, and
    factual consistency verification.
    
    :param formatted_message: The transcribed conversation text to generate a note from
    :type formatted_message: str
    
    :returns: True if note generation was successful, False otherwise
    :rtype: bool
    
    .. note::
        The behavior of this function depends on several application settings:
        - If 'use_aiscribe' is True, it generates a structured medical note
        - If 'Use Pre-Processing' is enabled, it first generates a list of facts
        - If 'Use Post-Processing' is enabled, it refines the generated note
        - Factual consistency verification is performed on the final note
    """
    try:
        summary = None
        current_prompt_info = NoteStyleSelector.get_current_prompt_info()
        if use_aiscribe:
            # If pre-processing is enabled
            if app_settings.editable_settings[SettingsKeys.USE_PRE_PROCESSING.value]:
                #Generate Facts List
                list_of_facts = send_text_to_chatgpt(f"{app_settings.editable_settings['Pre-Processing']} {formatted_message}", cancel_event)
                
                #Make a note from the facts
                medical_note = send_text_to_chatgpt(f"{current_prompt_info.pre_prompt} {list_of_facts} {current_prompt_info.post_prompt}", cancel_event)

                # If post-processing is enabled check the note over
                if app_settings.editable_settings["Use Post-Processing"]:
                    post_processed_note = send_text_to_chatgpt(f"{app_settings.editable_settings['Post-Processing']}\nFacts:{list_of_facts}\nNotes:{medical_note}", cancel_event)
                    summary = post_processed_note
                    update_gui_with_response(post_processed_note)
                else:
                    summary = medical_note
                    update_gui_with_response(medical_note)

            else: # If pre-processing is not enabled then just generate the note
                medical_note = send_text_to_chatgpt(f"{current_prompt_info.pre_prompt} {formatted_message} {current_prompt_info.post_prompt}", cancel_event)

                if app_settings.editable_settings["Use Post-Processing"]:
                    post_processed_note = send_text_to_chatgpt(f"{app_settings.editable_settings['Post-Processing']}\nNotes:{medical_note}", cancel_event)
                    update_gui_with_response(post_processed_note)
                    summary = post_processed_note
                else:
                    update_gui_with_response(medical_note)
                    summary = medical_note
        else: # do not generate note just send text directly to AI 
            ai_response = send_text_to_chatgpt(formatted_message, cancel_event)
            update_gui_with_response(ai_response)
            summary = ai_response

        check_and_warn_about_factual_consistency(formatted_message, summary)
            
        return True
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        safe_set_note_box(f"An error occurred: {e}")
        return False

def check_and_warn_about_factual_consistency(formatted_message: str, medical_note: str) -> None:
    """Verify and warn about potential factual inconsistencies in generated medical notes.

    This function checks the consistency between the original conversation and the generated
    medical note using multiple verification methods. If inconsistencies are found, a warning 
    dialog is shown to the user.

    :param formatted_message: The original transcribed conversation text
    :type formatted_message: str
    :param medical_note: The generated medical note to verify
    :type medical_note: str
    :returns: None

    .. note::
        The verification is only performed if factual consistency checking is enabled
        in the application settings.

    .. warning::
        Even if no inconsistencies are found, this does not guarantee the note is 100% accurate.
        Always review generated notes carefully.
    """
    # Verify factual consistency
    if not app_settings.editable_settings[SettingsKeys.FACTUAL_CONSISTENCY_VERIFICATION.value] or not FeatureToggle.FACTS_CHECK:
        return
        
    inconsistent_entities = find_factual_inconsistency(formatted_message, medical_note)
    logger.info(f"Inconsistent entities: {inconsistent_entities}")
    
    if inconsistent_entities:
        entities = '\n'.join(f'- {entity}' for entity in inconsistent_entities)
        warning_message = (
            "Heads-up: Potential inconsistencies detected in the generated note:\n\n"
            "Entities not in original conversation found:\n"
            f"{entities}"
            "\n\nPlease review the note for accuracy."
        )
        messagebox.showwarning("Factual Consistency Heads-up", warning_message)


def show_edit_transcription_popup(formatted_message):
    scrubber = scrubadub.Scrubber()

    scrubbed_message = scrubadub.clean(formatted_message)

    pattern = r'\b\d{10}\b'     # Any 10 digit number, looks like OHIP
    cleaned_message = re.sub(pattern, '{{OHIP}}', scrubbed_message)

    if (app_settings.editable_settings[SettingsKeys.LOCAL_LLM.value] or is_private_ip(
            app_settings.editable_settings[SettingsKeys.LLM_ENDPOINT.value])) and not app_settings.editable_settings["Show Scrub PHI"]:
        generate_note_thread(cleaned_message)
        return

    def on_proceed(edited_text):
        thread = threading.Thread(target=generate_note_thread, args=(edited_text,))
        thread.start()

    def on_cancel():
        stop_flashing()

    ScrubWindow(root, cleaned_message, on_proceed, on_cancel)


def generate_note_thread(text: str):
    """
    Generate a note from the given text and update the GUI with the response.

    :param text: The text to generate a note from.
    :type text: str
    """
    global GENERATION_THREAD_ID

    GENERATION_THREAD_ID = None

    cancel_event = threading.Event()

    def cancel_note_generation(thread_id, screen_thread):
        """Cancels any ongoing note generation.

        Sets the global flag to stop note generation operations.
        """
        global GENERATION_THREAD_ID

        try:
            # Set the cancellation event first
            cancel_event.set()
            
            if thread_id:
                kill_thread(thread_id)

            # check if screen thread is active before killing it
            if screen_thread and screen_thread.is_alive():
                kill_thread(screen_thread.ident)
                
            # Set the note box to client canceled
            safe_set_note_box("Note generation canceled.")
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
        finally:
            GENERATION_THREAD_ID = None
            stop_flashing()

    # Track the screen input thread
    screen_thread = None
    # The return value from the screen input thread
    screen_return = tk.BooleanVar()

    loading_window = LoadingWindow(root, "Screening Input Text", "Ensuring input is valid. Please wait.", on_cancel=lambda: (cancel_note_generation(GENERATION_THREAD_ID, screen_thread)))
    
    # screen input in its own thread so we can cancel it
    screen_thread = threading.Thread(target=threaded_screen_input, args=(text, screen_return))
    screen_thread.start()
    # wait for the thread to join/cancel so we can continue
    screen_thread.join()

    # Check if the screen input was canceled or force overridden by the user
    if screen_return.get() is False:
        loading_window.destroy()

        # display the popup
        if display_screening_popup() is False:
            return
    
    loading_window.destroy()
    loading_window = LoadingWindow(root, "Generating Note.", "Generating Note. Please wait.", on_cancel=lambda: (cancel_note_generation(GENERATION_THREAD_ID, screen_thread)))

    def generate_note_with_cleanup(text, cancel_event):
        """Wrapper function that ensures proper cleanup."""
        try:
            return generate_note(text, cancel_event)
        except Exception as e:
            logger.exception(f"Error in generate_note: {e}")
            return False
        finally:
            # Ensure the cancel event is set to stop any ongoing operations
            cancel_event.set()

    thread = threading.Thread(target=generate_note_with_cleanup, args=(text, cancel_event))
    thread.start()
    GENERATION_THREAD_ID = thread.ident

    def check_thread_status(thread, loading_window):
        if thread.is_alive():
            root.after(500, lambda: check_thread_status(thread, loading_window))
        else:
            loading_window.destroy()
            stop_flashing()
            # switch generate note button to "Regenerate Note"
            safe_set_button_config(send_button, text="Regenerate Note", bg=DEFAULT_BUTTON_COLOUR, state='normal')
    root.after(500, lambda: check_thread_status(thread, loading_window))

def upload_file():
    global uploaded_file_path
    file_path = filedialog.askopenfilename(filetypes=(("Audio files", "*.wav *.mp3 *.m4a"),))
    if file_path:
        uploaded_file_path = file_path
        threaded_send_audio_to_server()  # Add this line to process the file immediately
    start_flashing()


def start_flashing():
    global is_flashing
    is_flashing = True
    root.after(0, flash_circle())


def stop_flashing():
    global is_flashing
    is_flashing = False
    root.after(0, lambda: blinking_circle_canvas.itemconfig(circle, fill='white'))  # Reset to default color


def flash_circle():
    if not is_flashing:
        return
    def _flash_circle():
        current_color = blinking_circle_canvas.itemcget(circle, 'fill')
        new_color = 'blue' if current_color != 'blue' else 'black'
        blinking_circle_canvas.itemconfig(circle, fill=new_color)
        root.after(1000, flash_circle)  # Adjust the flashing speed as needed
    root.after(0, _flash_circle)


def send_and_flash():
    start_flashing()
    send_and_receive()


# Initialize variables to store window geometry for switching between views
last_full_position = None
last_minimal_position = None


def toggle_view():
    """
    Toggles the user interface between a full view and a minimal view.

    Full view includes all UI components, while minimal view limits the interface
    to essential controls, reducing screen space usage. The function also manages
    window properties, button states, and binds/unbinds hover events for transparency.
    """

    if current_view == "full":  # Transition to minimal view
        set_minimal_view()

    else:  # Transition back to full view
        set_full_view()


def set_full_view():
    """
    Configures the application to display the full view interface.

    Actions performed:
    - Reconfigure button dimensions and text.
    - Show all hidden UI components.
    - Reset window attributes such as size, transparency, and 'always on top' behavior.
    - Create the Docker status bar.
    - Restore the last known full view geometry if available.

    Global Variables:
    - current_view: Tracks the current interface state ('full' or 'minimal').
    - last_minimal_position: Saves the geometry of the window when switching from minimal view.
    """
    def action():
        global current_view, last_minimal_position, silent_warning_duration

        # Reset button sizes and placements for full view
        mic_button.config(width=11, height=2)
        pause_button.config(width=11, height=2)
        switch_view_button.config(width=11, height=2, text="Minimize View")

        # Show all UI components
        user_input.grid()
        send_button.grid()
        clear_button.grid()
        # toggle_button.grid()
        upload_button.grid()
        response_display.grid()
        history_frame.grid()
        mic_button.grid(row=1, column=1, pady=5, padx=0,sticky='nsew')
        pause_button.grid(row=1, column=2, pady=5, padx=0,sticky='nsew')
        switch_view_button.grid(row=1, column=6, pady=5, padx=0,sticky='nsew')
        blinking_circle_canvas.grid(row=1, column=7, padx=0,pady=5)
        footer_frame.grid()
        
        

        window.toggle_menu_bar(enable=True, is_recording=is_recording)

        # Reconfigure button styles and text
        mic_button.config(bg="red" if is_recording else DEFAULT_BUTTON_COLOUR,
                        text="Stop\nRecording" if is_recording else "Start\nRecording")
        pause_button.config(bg="red" if is_paused else DEFAULT_BUTTON_COLOUR,
                            text="Resume" if is_paused else "Pause")

        # Unbind transparency events and reset window properties
        root.unbind('<Enter>')  
        root.unbind('<Leave>')
        root.attributes('-alpha', 1.0)
        root.attributes('-topmost', False)
        root.minsize(900, 400)
        current_view = "full"

        #Recreates Silence Warning Bar
        window.destroy_warning_bar()
        check_silence_warning(silence_duration= silent_warning_duration)

        # add the minimal view geometry and remove the last full view geometry
        add_min_max(root)

        # create docker_status bar if enabled
        if app_settings.editable_settings["Use Docker Status Bar"]:
            window.create_docker_status_bar()

        # Save minimal view geometry and restore last full view geometry
        last_minimal_position = root.geometry()
        root.update_idletasks()
        if last_full_position:
            root.geometry(last_full_position)
        else:
            root.geometry("900x400")

        # Disable to make the window an app(show taskbar icon)
        # root.attributes('-toolwindow', False)

    root.after(0, action)

def set_minimal_view():
    """
    Configures the application to display the minimal view interface.

    Actions performed:
    - Reconfigure button dimensions and text.
    - Hide non-essential UI components.
    - Bind transparency hover events for better focus.
    - Adjust window attributes such as size, transparency, and 'always on top' behavior.
    - Destroy and optionally recreate specific components like the Scribe template.

    Global Variables:
    - current_view: Tracks the current interface state ('full' or 'minimal').
    - last_full_position: Saves the geometry of the window when switching from full view.
    """
    def action():
        global current_view, last_full_position, silent_warning_duration

        # Remove all non-essential UI components
        user_input.grid_remove()
        send_button.grid_remove()
        clear_button.grid_remove()
        # toggle_button.grid_remove()
        upload_button.grid_remove()
        response_display.grid_remove()
        history_frame.grid_remove()
        blinking_circle_canvas.grid_remove()
        footer_frame.grid_remove()
        # Configure minimal view button sizes and placements
        mic_button.config(width=2, height=1)
        pause_button.config(width=2, height=1)
        switch_view_button.config(width=2, height=1)

        mic_button.grid(row=0, column=0, pady=2, padx=2)
        pause_button.grid(row=0, column=1, pady=2, padx=2)
        switch_view_button.grid(row=0, column=2, pady=2, padx=2)

        # Update button text based on recording and pause states
        mic_button.config(text="⏹️" if is_recording else "🎤")
        pause_button.config(text="▶️" if is_paused else "⏸️")
        switch_view_button.config(text="⬆️")  # Minimal view indicator

        blinking_circle_canvas.grid(row=0, column=3, pady=2, padx=2)

        window.toggle_menu_bar(enable=False)

        # Update window properties for minimal view
        root.attributes('-topmost', True)
        root.minsize(125, 50)  # Smaller minimum size for minimal view
        current_view = "minimal"

        if root.wm_state() == 'zoomed':  # Check if window is maximized
            root.wm_state('normal')       # Restore the window

        #Recreates Silence Warning Bar
        window.destroy_warning_bar()
        check_silence_warning(silence_duration= silent_warning_duration)

        # Set hover transparency events
        def on_enter(e):
            if e.widget == root:  # Ensure the event is from the root window
                root.attributes('-alpha', 1.0)

        def on_leave(e):
            if e.widget == root:  # Ensure the event is from the root window
                root.attributes('-alpha', 0.70)

        root.bind('<Enter>', on_enter)
        root.bind('<Leave>', on_leave)

        # Destroy and re-create components as needed
        window.destroy_docker_status_bar()

        # Remove the minimal view geometry and save the current full view geometry
        remove_min_max(root)

        # Save full view geometry and restore last minimal view geometry
        last_full_position = root.geometry()
        if last_minimal_position:
            root.geometry(last_minimal_position)
        else:
            root.geometry("125x50")  # Set the window size to the minimal view size
    root.after(0, action)


def copy_text(widget):
    """
    Copy text content from a tkinter widget to the system clipboard.

    Args:
        widget: A tkinter Text widget containing the text to be copied.
    """
    text = widget.get("1.0", tk.END)
    try:
        pyperclip.copy(text)
    except Exception as e:
        logger.warning(str(e))


def add_placeholder(event, text_widget, placeholder_text="Text box"):
    """
    Add placeholder text to a tkinter Text widget when it's empty.

    Args:
        event: The event that triggered this function.
        text_widget: The tkinter Text widget to add placeholder text to.
        placeholder_text (str, optional): The placeholder text to display. Defaults to "Text box".
    """
    def on_call(text_widget=text_widget, placeholder_text=placeholder_text):
        if text_widget.get("1.0", "end-1c") == "":
            text_widget.insert("1.0", placeholder_text)

    root.after(0, on_call)

def remove_placeholder(event, text_widget, placeholder_text="Text box"):
    """
    Remove placeholder text from a tkinter Text widget when it gains focus.

    Args:
        event: The event that triggered this function.
        text_widget: The tkinter Text widget to remove placeholder text from.
        placeholder_text (str, optional): The placeholder text to remove. Defaults to "Text box".
    """
    def on_call(text_widget=text_widget, placeholder_text=placeholder_text):
        if text_widget.get("1.0", "end-1c") == placeholder_text:
            text_widget.delete("1.0", "end")
            
    root.after(0, on_call)

# Configure grid weights for scalability
root.grid_columnconfigure(0, weight=1, minsize=10)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_columnconfigure(3, weight=1)
root.grid_columnconfigure(4, weight=1)
root.grid_columnconfigure(5, weight=1)
root.grid_columnconfigure(6, weight=1)
root.grid_columnconfigure(7, weight=1)
root.grid_columnconfigure(8, weight=1)
root.grid_columnconfigure(9, weight=1)
root.grid_columnconfigure(10, weight=1)
root.grid_columnconfigure(11, weight=1, minsize=10)
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=0)
root.grid_rowconfigure(2, weight=1)
root.grid_rowconfigure(3, weight=0)
root.grid_rowconfigure(4, weight=0)


window.load_main_window()

user_input = CustomTextBox(root, height=12)
user_input.grid(row=0, column=1, columnspan=8, padx=5, pady=15, sticky='nsew')


# Insert placeholder text
user_input.scrolled_text.insert("1.0", "Transcript of Conversation")

# Bind events to remove or add the placeholder with arguments
user_input.scrolled_text.bind(
    "<FocusIn>",
    lambda event: remove_placeholder(
        event,
        user_input.scrolled_text,
        "Transcript of Conversation"))
user_input.scrolled_text.bind(
    "<FocusOut>",
    lambda event: add_placeholder(
        event,
        user_input.scrolled_text,
        "Transcript of Conversation"))

mic_button = tk.Button(root, text="Start\nRecording", height=2, width=11)
mic_button.configure(command=lambda: threaded_toggle_recording(mic_button))
mic_button.grid(row=1, column=1, pady=5, sticky='nsew')

send_button = tk.Button(root, text="Generate Note", command=send_and_flash, height=2, width=11)
send_button.grid(row=1, column=3, pady=5, sticky='nsew')

pause_button = tk.Button(root, text="Pause", command=toggle_pause, height=2, width=11)
pause_button.grid(row=1, column=2, pady=5, sticky='nsew')

clear_button = tk.Button(root, text="Clear", command=clear_application_press, height=2, width=11)
clear_button.grid(row=1, column=4, pady=5, sticky='nsew')

# hidding the AI Scribe button
# toggle_button = tk.Button(root, text="AI Scribe\nON", command=toggle_aiscribe, height=2, width=11)
# toggle_button.grid(row=1, column=5, pady=5, sticky='nsew')

upload_button = tk.Button(root, text="Upload Audio\nFor Transcription", command=upload_file, height=2, width=11)
upload_button.grid(row=1, column=5, pady=5, sticky='nsew')

switch_view_button = tk.Button(root, text="Minimize View", command=toggle_view, height=2, width=11)
switch_view_button.grid(row=1, column=6, pady=5, sticky='nsew')

blinking_circle_canvas = tk.Canvas(root, width=20, height=20)
blinking_circle_canvas.grid(row=1, column=7, pady=5)
circle = blinking_circle_canvas.create_oval(5, 5, 15, 15, fill='white')

response_display = CustomTextBox(root, height=13, state="disabled")
response_display.grid(row=2, column=1, columnspan=8, padx=5, pady=15, sticky='nsew')

# Insert placeholder text
response_display.scrolled_text.configure(state='normal')
response_display.scrolled_text.insert("1.0", "Medical Note")
response_display.scrolled_text.configure(state='disabled')


# Create a frame to hold both timestamp listbox and mic test
history_frame = ttk.Frame(root)
history_frame.grid(row=0, column=9, columnspan=2, rowspan=6, padx=5, pady=10, sticky='nsew')

# Configure the frame's grid
history_frame.grid_columnconfigure(0, weight=1)
history_frame.grid_rowconfigure(0, weight=4)  # Timestamp takes more space
history_frame.grid_rowconfigure(1, weight=1)
history_frame.grid_rowconfigure(2, weight=1)  # Mic test takes less space
history_frame.grid_rowconfigure(3, weight=1)

system_font = tk.font.nametofont("TkDefaultFont")
base_size = system_font.cget("size")
scaled_size = int(base_size * 0.9)  # 90% of system font size

# Add warning label
warning_label = tk.Label(history_frame,
                         text="Temporary Note History will be cleared when app closes",
                         # fg="red",
                         # wraplength=200,
                         justify="left",
                         font=tk.font.Font(size=scaled_size),
                         )
warning_label.grid(row=3, column=0, sticky='ew', pady=(0, 5))

# Add the timestamp listbox
timestamp_listbox = TimestampListbox(history_frame, height=30, exportselection=False, response_history=response_history)
timestamp_listbox.grid(row=0, column=0, rowspan=3, sticky='nsew')
timestamp_listbox.bind('<<ListboxSelect>>', show_response)
timestamp_listbox.insert(tk.END, "Temporary Note History")

warning_label = tk.Label(history_frame,
                            text="Temporary Note History will be cleared when app closes",
                            # fg="red",
                            # wraplength=200,
                            justify="left",
                            font=tk.font.Font(size=scaled_size),
                            )

def on_click_clear_all_notes():
    """
    Callback function to clear all notes from the timestamp listbox and response display.
    """
    # Disclaimer that all notes will be deleted
    if messagebox.askyesno("Clear All Notes", "Are you sure you want to delete all notes? You will not be able to undo or recover the notes."):
        clear_all_notes()


clear_all_notes_btn = tk.Button(history_frame, text="Clear All Notes", command=on_click_clear_all_notes, width=20, height=2)

def grid_clear_all_btn():
    """
    Function to grid the clear all notes button after the UI is initialized.
    """
    def action():
        clear_all_notes_btn.grid(row=3, column=0, sticky='ew', pady=5)

    root.after(0, action)

def grid_warning_label():
    """
    Function to grid the warning label after the UI is initialized.
    """
    def action():
        warning_label.grid(row=3, column=0, sticky='ew', pady=(0,5))

    root.after(0, action)

if not app_settings.editable_settings[SettingsKeys.STORE_NOTES_LOCALLY.value]:
    grid_warning_label()
else:
    grid_clear_all_btn()

# Add microphone test frame
mic_test = MicrophoneTestFrame(parent=history_frame, p=p, app_settings=app_settings, root=root)
mic_test.frame.grid(row=4, column=0, pady=10, sticky='nsew')  # Use grid to place the frame

# Add a footer frame at the bottom of the window
footer_frame = tk.Frame(root, bg="lightgrey", height=30)
footer_frame.grid(row=100, column=0, columnspan=100, sticky="ew")

# Configure footer frame grid columns
# Left spacer
footer_frame.grid_columnconfigure(0, weight=1)  
# NoteStyleSelector (center)
footer_frame.grid_columnconfigure(1, weight=0) 
# Right spacer 
footer_frame.grid_columnconfigure(2, weight=1) 

# Add NoteStyleSelector in the center of the footer
note_style_selector = NoteStyleSelector(root, footer_frame)
note_style_selector.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

# Add version label in a small box in the bottom right
version = get_application_version()
version_frame = tk.Frame(footer_frame, bg="lightgrey", relief="sunken", bd=1)
version_frame.grid(row=0, column=2, sticky="e", padx=5, pady=2)

version_label = tk.Label(
    version_frame,
    text=f"FreeScribe Client {version}",
    bg="lightgrey",
    font=("Arial", 8),
    padx=5,
    pady=2
)
version_label.pack()

# Bind Alt+P to send_and_receive function
root.bind('<Alt-p>', lambda event: pause_button.invoke())

# Bind Alt+R to toggle_recording function
root.bind('<Alt-r>', lambda event: mic_button.invoke())

# set min size
root.minsize(900, 400)

# ram checkj
if utils.system.is_system_low_memory() and not app_settings.is_low_mem_mode():
    logger.warning("System has low memory.")

    popup_box = PopupBox(root, 
    title="Low Memory Warning", 
    message="Your system has low memory. Please consider enabling Low Memory Mode in the settings.",
    button_text_1="Enable",
    button_text_2="Dismiss",
    )

    if popup_box.response == "button_1":
        app_settings.editable_settings[SettingsKeys.USE_LOW_MEM_MODE.value] = True
        app_settings.save_settings_to_file()
        logger.debug("Low Memory Mode enabled.")

if (app_settings.editable_settings['Show Welcome Message']):
    window.show_welcome_message()

#Wait for the UI root to be intialized then load the model. If using local llm.
# Do not load the models if low mem is activated.
if not app_settings.is_low_mem_mode():
    # Wait for the UI root to be intialized then load the model. If using local llm.
    if app_settings.editable_settings[SettingsKeys.LOCAL_LLM.value]:
        def on_cancel_llm_load():
            cancel_await_thread.set()
        root.after(
            100,
            lambda: (
                ModelManager.setup_model(
                    app_settings=app_settings,
                    root=root,
                    on_cancel=on_cancel_llm_load)))

    if app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]:
        # Inform the user that Local Whisper is being used for transcription
        print("Using Local Whisper for transcription.")
        root.after(100, lambda: (load_model_with_loading_screen(root=root, app_settings=app_settings)))

if app_settings.editable_settings[SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value] and FeatureToggle.HALLUCINATION_CLEANING:
    root.after(100, lambda: (
        load_hallucination_cleaner_model(root, app_settings)))

if app_settings.editable_settings[SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value] and FeatureToggle.HALLUCINATION_CLEANING:
    root.after(100, lambda: (
        load_hallucination_cleaner_model(root, app_settings)))

# wait for both whisper and llm to be loaded before unlocking the settings button
def await_models(timeout_length=60):
    """
    Waits until the necessary models (Whisper and LLM) are fully loaded.

    The function checks if local models are enabled based on application settings.
    If a remote model is used, the corresponding flag is set to True immediately,
    bypassing the wait. Otherwise, the function enters a loop that periodically
    checks for model readiness and prints status updates until both models are loaded.

    :return: None
    """

    if not hasattr(await_models, "start_timer"):
        await_models.start_timer = time.time()

    # if we cancel this thread then break out of the loop
    if cancel_await_thread.is_set():
        logger.info("*** Model loading cancelled. Enabling settings bar.")
        #reset the flag
        cancel_await_thread.clear()
        # reset the settings bar
        window.enable_settings_menu()
        # return so the .after() doesnt get called.
        return

    # if we are using remote whisper then we can assume it is loaded and dont wait
    whisper_loaded = (not app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value] or is_whisper_valid())

    # if we are not using local llm then we can assume it is loaded and dont wait
    llm_loaded = (not app_settings.editable_settings[SettingsKeys.LOCAL_LLM.value] or ModelManager.is_llm_valid())

    # Check for errors in models
    whisper_error = get_whisper_model() == WhisperModelStatus.ERROR
    llm_error = ModelManager.local_model == ModelStatus.ERROR

    logger.debug("*** Model loading status: ")
    logger.debug(f"Whisper loaded: {whisper_loaded}, Whisper Error Status:{whisper_error}, LLM loaded: {llm_loaded}, LLM Error status: {llm_error}")

    elapsed_time = time.time() - await_models.start_timer
    
    # Check if we should show error dialog (timeout OR any model error)
    should_show_error = (elapsed_time >= timeout_length) or \
        (whisper_error and llm_loaded) or \
        (llm_error and whisper_loaded) or \
        (llm_error and whisper_error)

    # wait for both models to be loaded
    if (not whisper_loaded or not llm_loaded) and not app_settings.is_low_mem_mode():
        if math.floor(elapsed_time) % 5 == 0:
            logger.info(f"Waiting for models to load. Loading timer: {math.floor(elapsed_time)}, Timeout:{timeout_length}")

        if should_show_error:
            # Gather diagnostic information about which models failed
            failed_models = []
            if (not whisper_loaded and app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]) or whisper_error:
                failed_models.append("Whisper (STT)")
            if (not llm_loaded and app_settings.editable_settings[SettingsKeys.LOCAL_LLM.value]) or llm_error:
                failed_models.append("LLM")
            
            failed_models_str = ', '.join(failed_models) if failed_models else 'Unknown'
            
            if elapsed_time >= timeout_length:
                error_message = f"Models failed to load within {timeout_length} seconds."
            else:
                error_message = "One or more models failed to load due to errors."
            
            logger.error(
                f"{error_message} "
                f"Failed models: {failed_models_str}. "
                "Please check your settings."
            )
            
            try:
                messagebox.showerror(
                    "Model Loading Error",
                    f"{error_message}\n\n"
                    f"Failed models: {failed_models_str}\n\n"
                    "The settings menu has been re-enabled. Please check your configuration and try again."
                )
            except Exception as e:
                logger.warning(f"Failed to show error notification dialog: {e}")
            finally:
                # Ensure settings menu is always enabled, regardless of success or failure
                window.enable_settings_menu()
            return

        try:
            # override the lock in case something else tried to edit
            window.disable_settings_menu()
            root.after(1000, await_models)
        except Exception as e:
            logger.exception(f"Error in model loading loop: {e}")
            # Ensure settings menu is enabled if there's an error
            window.enable_settings_menu()
            raise
    else:
        logger.info("*** Models loaded successfully on startup.")

        # if error null out the model
        if ModelManager.local_model == ModelStatus.ERROR:
            ModelManager.local_model = None
        
        if get_whisper_model() == WhisperModelStatus.ERROR:
            set_whisper_model(None)

        window.enable_settings_menu()


root.after(100, await_models)

root.bind("<<LoadSttModel>>", lambda e: load_stt_model(e, app_settings=app_settings))
root.bind("<<UnloadSttModel>>", unload_stt_model)

def generate_note_bind(event, data: np.ndarray):
    """
    Generate a note based on the current user input and update the response display.

    Args:
        event: Optional event parameter for binding to tkinter events.
    """
    loading_window = LoadingWindow(root, "Transcribing Audio", "Transcribing Audio. Please wait.", on_cancel=clear_application_press)
    
    def action():
        clear_application_press()

        wav_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768

        result = faster_whisper_transcribe(wav_data)

        update_gui(result)

    wrk_thrd = threading.Thread(target=action)
    wrk_thrd.start()

    def check_thread():
        if wrk_thrd.is_alive():
            root.after(100, check_thread)
        else:
            loading_window.destroy()
            send_and_receive()

    check_thread()

                           
root.bind("<<GenerateNote>>", lambda e: threading.Thread(target=lambda: generate_note_bind(e, RecordingsManager.last_selected_data)).start())

if app_settings.editable_settings[SettingsKeys.STORE_NOTES_LOCALLY.value]:
    # Load temporary notes from the file
    load_notes_history()
    # Populate the UI with the loaded notes
    populate_ui_with_notes()

window._init_post_load()

root.mainloop()

p.terminate()
