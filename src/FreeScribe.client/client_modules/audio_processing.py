import os
import threading
import time
import tkinter as tk
import wave
from tkinter import messagebox as messagebox, filedialog

import numpy as np
import requests
import torch

import utils.audio
from UI.LoadingWindow import LoadingWindow
from UI.SettingsConstant import SettingsKeys
from UI.SettingsWindow import SettingsWindow

from UI.Widgets.MicrophoneTestFrame import MicrophoneTestFrame
from client_modules.tools import kill_thread
from client_modules.ui_handlers import disable_recording_ui_elements, enable_recording_ui_elements, \
    start_flashing, stop_flashing, check_silence_warning, clear_all_text_fields
from client_modules.app_context import AppContext, AppConstants, AppUIComponents
from client_modules.transcription import threaded_check_stt_model, threaded_realtime_text, faster_whisper_transcribe
from client_modules.llm_integration import send_and_receive

from utils.file_utils import get_resource_path
from utils.log_config import logger
from utils.utils import close_mutex


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
            logger.error(f"Error deleting temporary file {filename}: {e}")


def on_closing():
    delete_temp_file('recording.wav')
    delete_temp_file('realtime.wav')
    close_mutex()


def threaded_toggle_recording():
    logger.debug(f"*** Toggle Recording - Recording status: {AppContext.is_recording}, STT local model: {AppContext.stt_local_model}")
    ready_flag = threaded_check_stt_model()
    # there is no point start recording if we are using local STT model and it's not ready
    # if user chooses to cancel the double check process, we need to return and not start recording
    if not ready_flag:
        return
    thread = threading.Thread(target=toggle_recording)
    thread.start()


def threaded_send_audio_to_server():
    thread = threading.Thread(target=send_audio_to_server)
    thread.start()
    return thread


def toggle_pause():
    AppContext.is_paused = not AppContext.is_paused

    if AppContext.is_paused:
        if AppContext.current_view == "full":
            AppUIComponents.pause_button.config(text="Resume", bg="red")
        elif AppContext.current_view == "minimal":
            AppUIComponents.pause_button.config(text="▶️", bg="red")
    else:
        if AppContext.current_view == "full":
            AppUIComponents.pause_button.config(text="Pause", bg=AppConstants.DEFAULT_BUTTON_COLOUR)
        elif AppContext.current_view == "minimal":
            AppUIComponents.pause_button.config(text="⏸️", bg=AppConstants.DEFAULT_BUTTON_COLOUR)


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
        stream = AppContext.p.open(
            format=AppConstants.FORMAT,
            channels=1,
            rate=AppConstants.RATE,
            input=True,
            frames_per_buffer=AppConstants.CHUNK,
            input_device_index=int(selected_index))

        return stream, None
    except (OSError, IOError) as e:
        # Log the error message
        # TODO System logger
        logger.error(f"An error occurred opening the stream({type(e).__name__}): {e}")
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

    try:
        current_chunk = []
        silent_duration = 0
        record_duration = 0
        minimum_silent_duration = int(AppContext.app_settings.editable_settings["Real Time Silence Length"])
        minimum_audio_duration = int(AppContext.app_settings.editable_settings["Real Time Audio Length"])

        stream, stream_exception = open_microphone_stream()

        if stream is None:
            clear_application_press()
            messagebox.showerror("Error", f"An error occurred while trying to record audio: {stream_exception}")

        audio_data_leng = 0
        while AppContext.is_recording and stream is not None:
            if not AppContext.is_paused:
                data = stream.read(AppConstants.CHUNK, exception_on_overflow=False)
                AppContext.frames.append(data)
                # Check for silence
                audio_buffer = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768

                # convert the setting from str to float
                try:
                    speech_prob_threshold = float(
                        AppContext.app_settings.editable_settings[SettingsKeys.SILERO_SPEECH_THRESHOLD.value])
                except ValueError:
                    # default it to value in DEFAULT_SETTINGS_TABLE on invalid error
                    speech_prob_threshold = AppContext.app_settings.DEFAULT_SETTINGS_TABLE[SettingsKeys.SILERO_SPEECH_THRESHOLD.value]

                if is_silent(audio_buffer, speech_prob_threshold ):
                    silent_duration += AppConstants.CHUNK / AppConstants.RATE
                    AppContext.silent_warning_duration += AppConstants.CHUNK / AppConstants.RATE
                else:
                    silent_duration = 0
                    AppContext.silent_warning_duration = 0
                    audio_data_leng += AppConstants.CHUNK / AppConstants.RATE

                current_chunk.append(data)

                record_duration += AppConstants.CHUNK / AppConstants.RATE

                # Check if we need to warn if silence is long than warn time
                check_silence_warning(AppContext.silent_warning_duration)

                # 1 second of silence at the end so we dont cut off speech
                if silent_duration >= minimum_silent_duration and audio_data_leng > 1.5  and record_duration > minimum_audio_duration:
                    if AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value] and current_chunk:
                        padded_audio = utils.audio.pad_audio_chunk(current_chunk, pad_seconds=0.5)
                        AppContext.audio_queue.put(b''.join(padded_audio))

                    # Carry over the last .1 seconds of audio to the next one so next speech does not start abruptly or in middle of a word
                    carry_over_chunk = current_chunk[-int(0.1 * AppConstants.RATE / AppConstants.CHUNK):]
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
            AppContext.audio_queue.put(b''.join(current_chunk))
    except Exception as e:
        # Log the error message
        # TODO System logger
        # For now general catch on any problems
        logger.error(f"An error occurred: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        AppContext.audio_queue.put(None)

        # If the warning bar is displayed, remove it
        if AppContext.window.warning_bar is not None:
            AppContext.window.destroy_warning_bar()


def is_silent(data, threshold: float = 0.65):
    """Check if audio chunk contains speech using Silero VAD"""
    # Convert audio data to tensor and ensure correct format
    audio_tensor = torch.FloatTensor(data)
    if audio_tensor.dim() == 2:
        audio_tensor = audio_tensor.mean(dim=1)

    # Get speech probability
    speech_prob = AppContext.silero(audio_tensor, 16000).item()
    return speech_prob < threshold


def save_audio():
    if AppContext.frames:
        with wave.open(get_resource_path("recording.wav"), 'wb') as wf:
            wf.setnchannels(AppConstants.CHANNELS)
            wf.setsampwidth(AppContext.p.get_sample_size(AppConstants.FORMAT))
            wf.setframerate(AppConstants.RATE)
            wf.writeframes(b''.join(AppContext.frames))
        AppContext.frames = []  # Clear recorded data

    if AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value] == True and AppContext.is_audio_processing_realtime_canceled.is_set() is False:
        send_and_receive()
    elif AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value] == False and AppContext.is_audio_processing_whole_canceled.is_set() is False:
        threaded_send_audio_to_server()


def toggle_recording():

    # Reset the cancel flags going into a fresh recording
    if not AppContext.is_recording:
        AppContext.is_audio_processing_realtime_canceled.clear()
        AppContext.is_audio_processing_whole_canceled.clear()

    if AppContext.is_paused:
        toggle_pause()

    realtime_thread = threaded_realtime_text()

    if not AppContext.is_recording:
        disable_recording_ui_elements()
        AppContext.realtime_transcribe_thread_id = realtime_thread.ident
        AppUIComponents.user_input.scrolled_text.configure(state='normal')
        AppUIComponents.user_input.scrolled_text.delete("1.0", tk.END)
        if not AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value]:
            AppUIComponents.user_input.scrolled_text.insert(tk.END, "Recording")
        AppUIComponents.response_display.scrolled_text.configure(state='normal')
        AppUIComponents.response_display.scrolled_text.delete("1.0", tk.END)
        AppUIComponents.response_display.scrolled_text.configure(fg='black')
        AppUIComponents.response_display.scrolled_text.configure(state='disabled')
        AppContext.is_recording = True

        # reset frames before new recording so old data is not used
        AppContext.frames = []
        AppContext.silent_warning_duration = 0
        AppContext.recording_thread = threading.Thread(target=record_audio)
        AppContext.recording_thread.start()


        if AppContext.current_view == "full":
            AppUIComponents.mic_button.config(bg="red", text="Stop\nRecording")
        elif AppContext.current_view == "minimal":
            AppUIComponents.mic_button.config(bg="red", text="⏹️")

        start_flashing()
    else:
        enable_recording_ui_elements()
        AppContext.is_recording = False
        if AppContext.recording_thread.is_alive():
            AppContext.recording_thread.join()  # Ensure the recording thread is terminated

        if AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value] and not AppContext.is_audio_processing_realtime_canceled.is_set():
            def cancel_realtime_processing(thread_id):
                """Cancels any ongoing audio processing.

                Sets the global flag to stop audio processing operations.
                """

                try:
                    kill_thread(thread_id)
                except Exception as e:
                    # Log the error message
                    # TODO System logger
                    logger.error(f"An error occurred: {e}")
                finally:
                    AppContext.realtime_transcribe_thread_id = None

                #empty the queue
                while not AppContext.audio_queue.empty():
                    AppContext.audio_queue.get()
                    AppContext.audio_queue.task_done()

            loading_window = LoadingWindow(AppContext.root, "Processing Audio", "Processing Audio. Please wait.", on_cancel=lambda: (cancel_processing(), cancel_realtime_processing(
                AppContext.realtime_transcribe_thread_id)))

            try:
                timeout_length = int(
                    AppContext.app_settings.editable_settings[SettingsKeys.AUDIO_PROCESSING_TIMEOUT_LENGTH.value])
            except ValueError:
                # default to 3minutes
                timeout_length = 180

            timeout_timer = 0.0
            while AppContext.audio_queue.empty() is False and timeout_timer < timeout_length:
                # break because cancel was requested
                if AppContext.is_audio_processing_realtime_canceled.is_set():
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

        if AppContext.current_view == "full":
            AppUIComponents.mic_button.config(bg=AppConstants.DEFAULT_BUTTON_COLOUR, text="Start\nRecording")
        elif AppContext.current_view == "minimal":
            AppUIComponents.mic_button.config(bg=AppConstants.DEFAULT_BUTTON_COLOUR, text="🎤")


def cancel_processing():
    """Cancels any ongoing audio processing.

    Sets the global flag to stop audio processing operations.
    """
    logger.info("Processing canceled.")

    if AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value]:
        AppContext.is_audio_processing_realtime_canceled.set() # Flag to terminate processing
    else:
        AppContext.is_audio_processing_whole_canceled.set()  # Flag to terminate processing


def reset_recording_status():
    """Resets all recording-related variables and stops any active recording.

    Handles cleanup of recording state by:
        - Checking if recording is active
        - Canceling any processing
        - Stopping the recording thread
    """
    if AppContext.is_recording:  # Only reset if currently recording
        cancel_processing()  # Stop any ongoing processing
        threaded_toggle_recording()  # Stop the recording thread

    # kill the generation thread if active
    if AppContext.realtime_transcribe_thread_id:
        # Exit the current realtime thread
        try:
            kill_thread(AppContext.realtime_transcribe_thread_id)
        except Exception as e:
            # Log the error message
            # TODO System logger
            logger.error(f"An error occurred: {e}")
        finally:
            AppContext.realtime_transcribe_thread_id = None

    if AppContext.generation_thread_id:
        try:
            kill_thread(AppContext.generation_thread_id)
        except Exception as e:
            # Log the error message
            # TODO System logger
            logger.error(f"An error occurred: {e}")
        finally:
            AppContext.generation_thread_id = None


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

    # nonlocal uploaded_file_path
    current_thread_id = threading.current_thread().ident

    def cancel_whole_audio_process(thread_id):

        AppContext.is_audio_processing_whole_canceled.clear()

        try:
            kill_thread(thread_id)
        except Exception as e:
            # Log the error message
            #TODO Logging the message to system logger
            logger.error(f"An error occurred: {e}")
        finally:
            AppContext.generation_thread_id = None
            clear_application_press()
            stop_flashing()

    loading_window = LoadingWindow(AppContext.root, "Processing Audio", "Processing Audio. Please wait.", on_cancel=lambda: (
    cancel_processing(), cancel_whole_audio_process(current_thread_id)))

    # Check if SettingsKeys.LOCAL_WHISPER is enabled in the editable settings
    if AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value] == True:
        # Inform the user that SettingsKeys.LOCAL_WHISPER.value is being used for transcription
        logger.info(f"Using {SettingsKeys.LOCAL_WHISPER.value} for transcription.")
        # Configure the user input widget to be editable and clear its content
        AppUIComponents.user_input.scrolled_text.configure(state='normal')
        AppUIComponents.user_input.scrolled_text.delete("1.0", tk.END)

        # Display a message indicating that audio to text processing is in progress
        AppUIComponents.user_input.scrolled_text.insert(tk.END, "Audio to Text Processing...Please Wait")
        try:
            # Determine the file to send for transcription
            file_to_send = AppContext.uploaded_file_path or get_resource_path('recording.wav')
            delete_file = False if AppContext.uploaded_file_path else True
            AppContext.uploaded_file_path = None

            # Transcribe the audio file using the loaded model
            try:
                result = faster_whisper_transcribe(file_to_send)
            except Exception as e:
                result = f"An error occurred ({type(e).__name__}): {e}"

            transcribed_text = result

            # done with file clean up
            if os.path.exists(file_to_send) and delete_file is True:
                os.remove(file_to_send)

            #check if canceled, if so do not update the UI
            if not AppContext.is_audio_processing_whole_canceled.is_set():
                # Update the user input widget with the transcribed text
                AppUIComponents.user_input.scrolled_text.configure(state='normal')
                AppUIComponents.user_input.scrolled_text.delete("1.0", tk.END)
                AppUIComponents.user_input.scrolled_text.insert(tk.END, transcribed_text)

                # Send the transcribed text and receive a response
                send_and_receive()
        except Exception as e:
            # Log the error message
            # TODO: Add system eventlogger
            logger.error(f"An error occurred: {e}")

            #log error to input window
            AppUIComponents.user_input.scrolled_text.configure(state='normal')
            AppUIComponents.user_input.scrolled_text.delete("1.0", tk.END)
            AppUIComponents.user_input.scrolled_text.insert(tk.END, f"An error occurred: {e}")
            AppUIComponents.user_input.scrolled_text.configure(state='disabled')
        finally:
            loading_window.destroy()

    else:
        # Inform the user that Remote Whisper is being used for transcription
        logger.info("Using Remote Whisper for transcription.")

        # Configure the user input widget to be editable and clear its content
        AppUIComponents.user_input.scrolled_text.configure(state='normal')
        AppUIComponents.user_input.scrolled_text.delete("1.0", tk.END)

        # Display a message indicating that audio to text processing is in progress
        AppUIComponents.user_input.scrolled_text.insert(tk.END, "Audio to Text Processing...Please Wait")

        delete_file = False if AppContext.uploaded_file_path else True

        # Determine the file to send for transcription
        if AppContext.uploaded_file_path:
            file_to_send = AppContext.uploaded_file_path
            AppContext.uploaded_file_path = None
        else:
            file_to_send = get_resource_path('recording.wav')

        # Open the audio file in binary mode
        with open(file_to_send, 'rb') as f:
            files = {'audio': f}

            # Add the Bearer token to the headers for authentication
            headers = {
                "Authorization": f"Bearer {AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_SERVER_API_KEY.value]}"
            }

            body = {
                "use_translate": AppContext.app_settings.editable_settings[SettingsKeys.USE_TRANSLATE_TASK.value],
            }

            if AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value] not in SettingsWindow.AUTO_DETECT_LANGUAGE_CODES:
                body["language_code"] = AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value]

            try:
                verify = not AppContext.app_settings.editable_settings[SettingsKeys.S2T_SELF_SIGNED_CERT.value]

                logger.info("Sending audio to server")
                logger.info("File informaton")
                logger.info(f"File: {file_to_send}")
                logger.info(f"File Size: {os.path.getsize(file_to_send)}")

                # Send the request without verifying the SSL certificate
                response = requests.post(
                    AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_ENDPOINT.value], headers=headers, files=files, verify=verify, data=body)

                logger.info(f"Response from whisper with status code: {response.status_code}")

                response.raise_for_status()

                # check if canceled, if so do not update the UI
                if not AppContext.is_audio_processing_whole_canceled.is_set():
                    # Update the UI with the transcribed text
                    transcribed_text = response.json()['text']
                    AppUIComponents.user_input.scrolled_text.configure(state='normal')
                    AppUIComponents.user_input.scrolled_text.delete("1.0", tk.END)
                    AppUIComponents.user_input.scrolled_text.insert(tk.END, transcribed_text)

                    # Send the transcribed text and receive a response
                    send_and_receive()
            except Exception as e:
                # log error message
                #TODO: Implment proper logging to system
                logger.error(f"An error occurred: {e}")
                # Display an error message to the user
                AppUIComponents.user_input.scrolled_text.configure(state='normal')
                AppUIComponents.user_input.scrolled_text.delete("1.0", tk.END)
                AppUIComponents.user_input.scrolled_text.insert(tk.END, f"An error occurred: {e}")
                AppUIComponents.user_input.scrolled_text.configure(state='disabled')
            finally:
                # done with file clean up
                f.close()
                if os.path.exists(file_to_send) and delete_file:
                    os.remove(file_to_send)
                loading_window.destroy()
    stop_flashing()


def upload_file():
    # nonlocal uploaded_file_path
    file_path = filedialog.askopenfilename(filetypes=(("Audio files", "*.wav *.mp3 *.m4a"),))
    if file_path:
        AppContext.uploaded_file_path = file_path
        threaded_send_audio_to_server()  # Add this line to process the file immediately
    start_flashing()


def clear_application_press():
    """Resets the application state by clearing text fields and recording status."""
    reset_recording_status()  # Reset recording-related variables
    clear_all_text_fields()  # Clear UI text areas
