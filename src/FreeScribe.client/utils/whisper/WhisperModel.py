"""
This software is released under the AGPL-3.0 license
Copyright (c) 2023-2025 Braedon Hendy

Further updates and packaging added in 2024-2025 through the ClinicianFOCUS initiative,
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied
Learning and Technology as part of the CNERG+ applied research project,
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform.
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner),
and Research Students (Software Developers) -
Alex Simko, Pemba Sherpa, Naitik Patel, Yogesh Kumar and Xun Zhong.
"""

import utils.decorators
from faster_whisper import WhisperModel
from faster_whisper.vad import (
    SpeechTimestampsMap,
    VadOptions,
    collect_chunks,
    get_speech_timestamps,
    merge_segments,
)
import torch
import threading
from UI.LoadingWindow import LoadingWindow
from UI.SettingsConstant import SettingsKeys, Architectures
import tkinter.messagebox as messagebox
import platform
import utils.system
import gc
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import utils.whisper.Constants
import UI.LoadingWindow
import numpy as np
from utils.log_config import logger
from enum import Enum


stt_local_model = None

stt_model_loading_thread_lock = threading.Lock()


WINDOWS_LINUX = ("Windows", "Linux")

SAMPLE_RATE = 16000


class TranscribeError(Exception):
    pass

class WhisperModelStatus(Enum):
    """
    Enum to represent the status of the Whisper model.
    """
    ERROR = 1

def get_selected_whisper_architecture(app_settings):
    """
    Determine the appropriate device architecture for the Whisper model.

    Returns:
        str: The architecture value (CPU or CUDA) based on user settings.
    """
    device_type = Architectures.CPU.architecture_value
    if (
        app_settings.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value]
        == Architectures.CUDA.label
    ):
        device_type = Architectures.CUDA.architecture_value

    return device_type


def load_model_with_loading_screen(root, app_settings):
    """
    Initialize speech-to-text model loading in a separate thread.

    Args:
        root: The root window to bind the loading screen to.
    """
    global stt_local_model
    try:
       model_id = get_model_from_settings(app_settings)
    except Exception as e:
        logger.exception("Failed to get model ID from settings")
        stt_local_model = WhisperModelStatus.ERROR
        return
    loading_screen = UI.LoadingWindow.LoadingWindow(
        root,
        title="Speech to Text",
        initial_text=f"Loading Speech to Text model ({model_id}).\n Please wait.",
        note_text="Note: If this is the first time loading the model, it will be actively downloading and may take some time.\n We appreciate your patience!",
    )

    load_thread = load_stt_model(app_settings=app_settings)

    # wait for load_thread to finish before closing loading screen

    def wait_for_loading_thread():
        nonlocal load_thread
        if load_thread.is_alive():
            root.after(100, wait_for_loading_thread)
        else:
            loading_screen.destroy()

    root.after(0, wait_for_loading_thread)


def load_stt_model(event=None, app_settings=None):
    """
    Initialize speech-to-text model loading in a separate thread.

    Args:
        event: Optional event parameter for binding to tkinter events.
    """

    if utils.system.is_windows() or utils.system.is_linux():
        load_func = _load_stt_model_windows
    elif utils.system.is_macos():
        load_func = _load_stt_model_macos
    else:
        raise NotImplementedError(f"Unsupported platform: {platform.system()}")
    thread = threading.Thread(target=load_func, args=(app_settings,))
    thread.start()
    return thread


@utils.decorators.macos_only
def _load_stt_model_macos(app_settings):
    """
    Internal function to load the Whisper speech-to-text model on MacOS.


    :param app_settings: The application settings
    :type app_settings: SettingsWindow
    """
    global stt_local_model

    # get the device metal if its avail else use cpu
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    torch_dtype = torch.float32

    # Model ID to load and pull from hugging face
    try:
        model_id = get_model_from_settings(app_settings)
    except Exception as e:
        logger.exception("Failed to get model ID from settings")
        stt_local_model = WhisperModelStatus.ERROR
        return
    print("Loading STT model: ", model_id)

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    )
    model.to(device)

    processor = AutoProcessor.from_pretrained(model_id)

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
        return_timestamps=True,
    )

    stt_local_model = pipe


@utils.decorators.os_only(WINDOWS_LINUX)
def _load_stt_model_windows(app_settings):
    """
    Internal function to load the Whisper speech-to-text model.

    Creates a loading window and handles the initialization of the WhisperModel
    with configured settings. Updates the global stt_local_model variable.

    Raises:
        Exception: Any error that occurs during model loading is caught, logged,
                  and displayed to the user via a message box.
    """
    global stt_local_model

    with stt_model_loading_thread_lock:

        try:
            model_name = get_model_from_settings(app_settings)
        except Exception as e:
            logger.exception("Failed to get model ID from settings")
            stt_local_model = WhisperModelStatus.ERROR
            return
        print(f"Loading STT model: {model_name}")

        try:
            unload_stt_model()
            device_type = get_selected_whisper_architecture(app_settings)
            utils.system.set_cuda_paths()

            compute_type = app_settings.editable_settings[
                SettingsKeys.WHISPER_COMPUTE_TYPE.value
            ]
            # Change the  compute type automatically if using a gpu one.
            if (
                device_type == Architectures.CPU.architecture_value
                and compute_type == "float16"
            ):
                compute_type = "int8"

            stt_local_model = WhisperModel(
                model_name,
                device=device_type,
                cpu_threads=int(
                    app_settings.editable_settings[SettingsKeys.WHISPER_CPU_COUNT.value]
                ),
                compute_type=compute_type,
            )

            print("STT model loaded successfully.")
        except Exception as e:
            print(f"An error occurred while loading STT {type(e).__name__}: {e}")
            stt_local_model = None
            messagebox.showerror(
                "Error",
                f"An error occurred while loading Speech to Text {type(e).__name__}: {e}",
            )
        finally:
            # window.enable_settings_menu()
            # stt_loading_window.destroy()
            print("Closing STT loading window.")


def unload_stt_model(event=None):
    """
    Unload the speech-to-text model from memory.

    Cleans up the global stt_local_model instance and performs garbage collection
    to free up system resources.
    """
    global stt_local_model
    if stt_local_model is not None:
        print("Unloading STT model from device.")
        # no risk of temporary "stt_local_model in globals() is False" with same gc effect
        stt_local_model = None
        gc.collect()

        if utils.system.is_macos():
            print("Clearing memory on MacOS.")
            torch.mps.empty_cache()  # Clear MPS memory (if on macOS)

        print("STT model unloaded successfully.")
    else:
        print("STT model is already unloaded.")


def faster_whisper_transcribe(audio, app_settings):
    """
    Transcribe audio using the Faster Whisper model.

    Args:
        audio: Audio data to transcribe.

    Returns:
        str: Transcribed text or error message if transcription fails.
    """
    if utils.system.is_windows() or utils.system.is_linux():
        return _faster_whisper_transcribe_windows(audio, app_settings)
    elif utils.system.is_macos():
        return _faster_whisper_transcribe_macos(audio, app_settings)
    else:
        raise NotImplementedError(f"Unsupported platform: {platform.system()}")


@utils.decorators.macos_only
def _faster_whisper_transcribe_macos(audio, app_settings):
    """
    Transcribe audio using the Faster Whisper model.

    Args:
        audio: Audio data to transcribe.

    Returns
        str: Transcribed text or error message if transcription fails.
    """
    # Remove silent chunks
    cleaned_audio = _remove_silent_chunks(audio)

    # passing arguments to translate
    generate_kwargs = {}
    if app_settings.editable_settings[SettingsKeys.USE_TRANSLATE_TASK.value]:
        generate_kwargs['task'] = 'translate'

    # Transcription
    result = stt_local_model(cleaned_audio, generate_kwargs=generate_kwargs)
    return result["text"]


def _remove_silent_chunks(audio: np.ndarray):
    """
    Remove silent chunks from audio using VAD.

    Args:
        audio: Audio data to process.

    Returns:
        np.ndarray: Processed audio data with silent chunks removed.
    """
    original_audio_duration = audio.shape[0] / SAMPLE_RATE

    # Load VAD parameters
    vad_params = VadOptions(
        max_speech_duration_s=30,
        min_silence_duration_ms=160,
    )

    # get active speech segments
    active_segments = get_speech_timestamps(audio, vad_params)
    clip_timestamps = merge_segments(active_segments, vad_params)
    # calculate duration after VAD
    duration_after_vad = (
        sum((segment["end"] - segment["start"]) for segment in clip_timestamps)
        / SAMPLE_RATE
    )

    logger.info(
        f"Original audio duration: {original_audio_duration:.2f}s, Duration after VAD: {duration_after_vad:.2f}s, Total segment time removed: {(original_audio_duration - duration_after_vad):.2f}s"
    )

    # collect audio chunks
    audio_chunks, meta_data = collect_chunks(audio, clip_timestamps)

    if audio_chunks is None:
        return audio

    # merge all audio_chuncks into one np.ndarray
    audio = np.concatenate(audio_chunks)

    return audio


@utils.decorators.os_only(WINDOWS_LINUX)
def _faster_whisper_transcribe_windows(audio, app_settings):
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
        # Validate beam_size
        try:
            beam_size = int(
                app_settings.editable_settings[SettingsKeys.WHISPER_BEAM_SIZE.value]
            )
            if beam_size <= 0:
                raise ValueError(
                    f"{SettingsKeys.WHISPER_BEAM_SIZE.value} must be greater than 0 in advanced settings"
                )
        except (ValueError, TypeError) as e:
            return f"Invalid {SettingsKeys.WHISPER_BEAM_SIZE.value} parameter. Please go into the advanced settings and ensure you have a integer greater than 0: {str(e)}"

        additional_kwargs = {}
        if app_settings.editable_settings[SettingsKeys.USE_TRANSLATE_TASK.value]:
            additional_kwargs["task"] = "translate"

        # Validate vad_filter
        vad_filter = bool(
            app_settings.editable_settings[SettingsKeys.WHISPER_VAD_FILTER.value]
        )

        segments, info = stt_local_model.transcribe(
            audio, beam_size=beam_size, vad_filter=vad_filter, **additional_kwargs
        )

        return "".join(f"{segment.text} " for segment in segments)
    except Exception as e:
        error_message = f"Transcription failed: {str(e)}"
        print(f"Error during transcription: {str(e)}")
        raise TranscribeError(error_message) from e


def is_whisper_valid():
    """
    Check if the Whisper model is valid and loaded.

    Returns:
        bool: True if the Whisper model is loaded and valid, False otherwise.
    """

    return stt_local_model is not None and stt_local_model != WhisperModelStatus.ERROR


def is_whisper_lock():
    """
    Check if the Whisper model is currently being loaded.

    Returns:
        bool: True if the Whisper model is being loaded, False otherwise.
    """
    return stt_model_loading_thread_lock.locked()


def get_model_from_settings(app_settings):
    """
    Get the model name from the app settings.

    Returns:
        str: The model name.
    """

    label_name = app_settings.editable_settings[SettingsKeys.WHISPER_MODEL.value]

    return utils.whisper.Constants.WhisperModels.find_by_label(
        label_name
    ).get_platform_value()

def get_whisper_model():
    """
    Get the currently loaded Whisper model.

    Returns:
        WhisperModel: The loaded Whisper model instance.
    """
   
    return stt_local_model

def set_whisper_model(model):
    """
    Set the Whisper model to a new instance.

    Args:
        model (WhisperModel): The new Whisper model instance to set.
    """
    global stt_local_model
    stt_local_model = model