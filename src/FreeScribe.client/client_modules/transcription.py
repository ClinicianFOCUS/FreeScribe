import gc
import io
import threading
import time
import tkinter as tk
import wave
from tkinter import messagebox

import numpy as np
import requests
from faster_whisper import WhisperModel

from UI.LoadingWindow import LoadingWindow
from UI.SettingsConstant import SettingsKeys, Architectures
from UI.SettingsWindow import SettingsWindow
from WhisperModel import TranscribeError

from client_modules.ui_handlers import update_gui

from client_modules.app_context import AppContext, AppConstants
from client_modules.tools import set_cuda_paths, get_selected_whisper_architecture
from services.whisper_hallucination_cleaner import hallucination_cleaner
from utils.log_config import logger


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
    AppContext.root.wait_variable(task_done_var)

    # Check if the task was canceled via task_cancel_var
    if task_cancel_var.get():
        logger.debug("double checking canceled")
        return False
    return True


def double_check_stt_model_loading(task_done_var, task_cancel_var):
    logger.info(f"*** Double Checking STT model - Model Current Status: {AppContext.stt_local_model}")
    stt_loading_window = None
    try:
        if AppContext.is_recording:
            logger.info("*** Recording in progress, skipping double check")
            return
        if not AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]:
            logger.info("*** Local Whisper is disabled, skipping double check")
            return
        if AppContext.stt_local_model:
            logger.info("*** STT model already loaded, skipping double check")
            return
        # if using local whisper and model is not loaded, when starting recording
        if AppContext.stt_model_loading_thread_lock.locked():
            model_name = AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_MODEL.value].strip()
            stt_loading_window = LoadingWindow(AppContext.root, "Loading Speech to Text model",
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
                if not AppContext.stt_model_loading_thread_lock.locked():
                    break
            stt_loading_window.destroy()
            stt_loading_window = None
        # double check
        if AppContext.stt_local_model is None:
            # mandatory loading, synchronous
            t = load_stt_model()
            t.join()

    except Exception as e:
        logger.exception(str(e))
        messagebox.showerror("Error",
                             f"An error occurred while loading Speech to Text model synchronously {type(e).__name__}: {e}")
    finally:
        logger.info(f"*** Double Checking STT model Complete - Model Current Status: {AppContext.stt_local_model}")
        if stt_loading_window:
            stt_loading_window.destroy()
        task_done_var.set(True)


def threaded_realtime_text():
    thread = threading.Thread(target=realtime_text)
    thread.start()
    return thread


def realtime_text():
    # Incase the user starts a new recording while this one the older thread is finishing.
    # This is a local flag to prevent the processing of the current audio chunk
    # if the global flag is reset on new recording
    local_cancel_flag = False
    if not AppContext.is_realtimeactive:
        AppContext.is_realtimeactive = True
        # this is the text that will be used to process intents
        intent_text = ""

        while True:
            #  break if canceled
            if AppContext.is_audio_processing_realtime_canceled.is_set():
                local_cancel_flag = True
                break

            audio_data = AppContext.audio_queue.get()
            if audio_data is None:
                break
            if AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_REAL_TIME.value] == True:
                logger.info("Real Time Audio to Text")
                audio_buffer = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768
                if AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value] == True:
                    logger.info(f"Local Real Time Whisper { AppContext.audio_queue.qsize()=}")
                    if AppContext.stt_local_model is None:
                        update_gui("Local Whisper model not loaded. Please check your settings.")
                        break
                    result = ""
                    try:
                        result = faster_whisper_transcribe(audio_buffer)
                    except Exception as e:
                        update_gui(f"\nError: {e}\n")

                    if not local_cancel_flag and not AppContext.is_audio_processing_realtime_canceled.is_set():
                        update_gui(result)
                        intent_text = result
                else:
                    logger.info("Remote Real Time Whisper")
                    buffer = io.BytesIO()
                    with wave.open(buffer, 'wb') as wf:
                        wf.setnchannels(AppConstants.CHANNELS)
                        wf.setsampwidth(AppContext.p.get_sample_size(AppConstants.FORMAT))
                        wf.setframerate(AppConstants.RATE)
                        wf.writeframes(audio_data)

                    buffer.seek(0) # Reset buffer position

                    files = {'audio': buffer}

                    headers = {
                        "Authorization": "Bearer " +
                                         AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_SERVER_API_KEY.value]
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
                        logger.info(f"File Size: {len(buffer.getbuffer())} bytes")

                        response = requests.post(
                            AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_ENDPOINT.value], headers=headers, files=files, verify=verify, data=body)

                        logger.info(f"Response from whisper with status code: {response.status_code}")

                        if response.status_code == 200:
                            text = response.json()['text']
                            if not local_cancel_flag and not AppContext.is_audio_processing_realtime_canceled.is_set():
                                update_gui(text)
                                intent_text = text
                        else:
                            update_gui(f"Error (HTTP Status {response.status_code}): {response.text}")
                    except Exception as e:
                        update_gui(f"Error: {e}")
                    finally:
                        #close buffer. we dont need it anymore
                        buffer.close()
                # Process intents
                try:
                    logger.debug(f"Processing intents for text: {intent_text}")
                    AppContext.window.get_text_intents(intent_text)
                except Exception as e:
                    logger.exception(f"Error processing intents: {e}")
            AppContext.audio_queue.task_done()
    else:
        AppContext.is_realtimeactive = False


def load_stt_model(event=None):
    """
    Initialize speech-to-text model loading in a separate thread.

    Args:
        event: Optional event parameter for binding to tkinter events.
    """
    thread = threading.Thread(target=_load_stt_model_thread)
    thread.start()
    return thread


def _load_stt_model_thread():
    """
    Internal function to load the Whisper speech-to-text model.

    Creates a loading window and handles the initialization of the WhisperModel
    with configured settings. Updates the global AppContext.stt_local_model variable.

    Raises:
        Exception: Any error that occurs during model loading is caught, logged,
                  and displayed to the user via a message box.
    """
    with AppContext.stt_model_loading_thread_lock:

        def on_cancel_whisper_load():
            AppContext.cancel_await_thread.set()

        model_name = AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_MODEL.value].strip()
        stt_loading_window = LoadingWindow(AppContext.root, title="Speech to Text", initial_text=f"Loading Speech to Text {model_name} model. Please wait.",
                                           note_text="Note: If this is the first time loading the model, it will be actively downloading and may take some time.\n We appreciate your patience!", on_cancel=on_cancel_whisper_load)
        AppContext.window.disable_settings_menu()
        logger.info(f"Loading STT model: {model_name}")

        try:
            unload_stt_model()
            device_type = get_selected_whisper_architecture()
            set_cuda_paths()

            compute_type = AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_COMPUTE_TYPE.value]
            # Change the  compute type automatically if using a gpu one.
            if device_type == Architectures.CPU.architecture_value and compute_type == "float16":
                compute_type = "int8"


            AppContext.stt_local_model = WhisperModel(
                model_name,
                device=device_type,
                cpu_threads=int(AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_CPU_COUNT.value]),
                compute_type=compute_type
            )

            logger.info("STT model loaded successfully.")
        except Exception as e:
            logger.error(f"An error occurred while loading STT {type(e).__name__}: {e}")
            AppContext.stt_local_model = None
            messagebox.showerror("Error", f"An error occurred while loading Speech to Text {type(e).__name__}: {e}")
        finally:
            AppContext.window.enable_settings_menu()
            stt_loading_window.destroy()
            logger.info("Closing STT loading window.")
        logger.debug(f"STT model status after loading: { AppContext.stt_local_model=}")


def unload_stt_model(event=None):
    """
    Unload the speech-to-text model from memory.

    Cleans up the global AppContext.stt_local_model instance and performs garbage collection
    to free up system resources.
    """
    if AppContext.stt_local_model is not None:
        logger.info("Unloading STT model from device.")
        AppContext.stt_local_model = None
        gc.collect()
        logger.info("STT model unloaded successfully.")
    else:
        logger.info("STT model is already unloaded.")
    logger.debug(f"STT model status after unloading: { AppContext.stt_local_model=}")


def faster_whisper_transcribe(audio):
    """
    Transcribe audio using the Faster Whisper model.

    Args:
        audio: Audio data to transcribe.

    Returns:
        str: Transcribed text or error message if transcription fails.

    Raises:
        Exception: Any error during transcription is caught and returned as an error message.
    """
    try:
        if AppContext.stt_local_model is None:
            load_stt_model()
            raise TranscribeError("Speech2Text model not loaded. Please try again once loaded.")

        # Validate beam_size
        try:
            beam_size = int(AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_BEAM_SIZE.value])
            if beam_size <= 0:
                raise ValueError(f"{SettingsKeys.WHISPER_BEAM_SIZE.value} must be greater than 0 in advanced settings")
        except (ValueError, TypeError) as e:
            return f"Invalid {SettingsKeys.WHISPER_BEAM_SIZE.value} parameter. Please go into the advanced settings and ensure you have a integer greater than 0: {str(e)}"

        additional_kwargs = {}
        if AppContext.app_settings.editable_settings[SettingsKeys.USE_TRANSLATE_TASK.value]:
            additional_kwargs['task'] = 'translate'
        if AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value] not in SettingsWindow.AUTO_DETECT_LANGUAGE_CODES:
            additional_kwargs['language'] = AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value]

        # Validate vad_filter
        vad_filter = bool(AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_VAD_FILTER.value])

        start_time = time.monotonic()
        segments, info = AppContext.stt_local_model.transcribe(
            audio,
            beam_size=beam_size,
            vad_filter=vad_filter,
            **additional_kwargs
        )
        if type(audio) in [str, np.ndarray]:
            logger.info(f"took {time.monotonic() - start_time:.3f} seconds to process {len(audio)=} {type(audio)=} audio.")

        result = "".join(f"{segment.text} " for segment in segments)
        logger.debug(f"Result: {result}")

        # Only clean hallucinations if enabled in settings
        if AppContext.app_settings.editable_settings[SettingsKeys.ENABLE_HALLUCINATION_CLEAN.value]:
            result = hallucination_cleaner.clean_text(result)
        return result
    except Exception as e:
        error_message = f"Transcription failed: {str(e)}"
        logger.error(f"Error during transcription: {str(e)}")
        raise TranscribeError(error_message) from e
