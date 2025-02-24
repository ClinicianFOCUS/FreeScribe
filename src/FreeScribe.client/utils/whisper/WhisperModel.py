import utils.decorators
from faster_whisper import WhisperModel
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

stt_local_model = None

stt_model_loading_thread_lock = threading.Lock()


class TranscribeError(Exception):
    pass


def get_selected_whisper_architecture(app_settings):
    """
    Determine the appropriate device architecture for the Whisper model.

    Returns:
        str: The architecture value (CPU or CUDA) based on user settings.
    """
    device_type = Architectures.CPU.architecture_value
    if app_settings.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value] == Architectures.CUDA.label:
        device_type = Architectures.CUDA.architecture_value

    return device_type


def load_model_with_loading_screen(root, app_settings):
    """
    Initialize speech-to-text model loading in a separate thread.

    Args:
        root: The root window to bind the loading screen to.
    """
    loading_screen = UI.LoadingWindow.LoadingWindow(root, title="Speech to Text", initial_text="Loading Speech to Text model. Please wait.",
                                                    note_text="Note: If this is the first time loading the model, it will be actively downloading and may take some time.\n We appreciate your patience!")

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

    if utils.system.is_windows():
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
    global stt_local_model
    # test_audio_path = r"/Users/alex/Downloads/Doctor-Patient Cost of Care Conversation.mp3"

    device = "mps" if torch.backends.mps.is_available() else "cpu"

    torch_dtype = torch.float32

    model_id = utils.whisper.Constants.WhisperModels.find_by_label(
        app_settings.editable_settings[SettingsKeys.WHISPER_MODEL.value]).get_platform_value()

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


@utils.decorators.windows_only
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

        def on_cancel_whisper_load():
            cancel_await_thread.set()

        model_name = utils.whisper.Constants.WhisperModels.find_by_label(
            app_settings.editable_settings[SettingsKeys.WHISPER_MODEL.value]).get_platform_value()
        # stt_loading_window = LoadingWindow(root, title="Speech to Text", initial_text=f"Loading Speech to Text {model_name} model. Please wait.",
        #                                    note_text="Note: If this is the first time loading the model, it will be actively downloading and may take some time.\n We appreciate your patience!", on_cancel=on_cancel_whisper_load)
        # window.disable_settings_menu()
        print(f"Loading STT model: {model_name}")

        try:
            unload_stt_model()
            device_type = get_selected_whisper_architecture(app_settings)
            utils.system.set_cuda_paths()

            compute_type = app_settings.editable_settings[SettingsKeys.WHISPER_COMPUTE_TYPE.value]
            # Change the  compute type automatically if using a gpu one.
            if device_type == Architectures.CPU.architecture_value and compute_type == "float16":
                compute_type = "int8"

            stt_local_model = WhisperModel(
                model_name,
                device=device_type,
                cpu_threads=int(app_settings.editable_settings[SettingsKeys.WHISPER_CPU_COUNT.value]),
                compute_type=compute_type
            )

            print("STT model loaded successfully.")
        except Exception as e:
            print(f"An error occurred while loading STT {type(e).__name__}: {e}")
            stt_local_model = None
            messagebox.showerror("Error", f"An error occurred while loading Speech to Text {type(e).__name__}: {e}")
        finally:
            # window.enable_settings_menu()
            # stt_loading_window.destroy()
            print("Closing STT loading window.")


def unload_stt_model():
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
    if utils.system.is_windows():
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
    # Perform transcription
    result = stt_local_model(audio)
    return result["text"]


@utils.decorators.windows_only
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
        if stt_local_model is None:
            load_model_with_loading_screen(root=root, app_settings=app_settings)
            raise TranscribeError("Speech2Text model not loaded. Please try again once loaded.")

        # Validate beam_size
        try:
            beam_size = int(app_settings.editable_settings[SettingsKeys.WHISPER_BEAM_SIZE.value])
            if beam_size <= 0:
                raise ValueError(f"{SettingsKeys.WHISPER_BEAM_SIZE.value} must be greater than 0 in advanced settings")
        except (ValueError, TypeError) as e:
            return f"Invalid {SettingsKeys.WHISPER_BEAM_SIZE.value} parameter. Please go into the advanced settings and ensure you have a integer greater than 0: {str(e)}"

        additional_kwargs = {}
        if app_settings.editable_settings[SettingsKeys.USE_TRANSLATE_TASK.value]:
            additional_kwargs['task'] = 'translate'

        # Validate vad_filter
        vad_filter = bool(app_settings.editable_settings[SettingsKeys.WHISPER_VAD_FILTER.value])

        segments, info = stt_local_model.transcribe(
            audio,
            beam_size=beam_size,
            vad_filter=vad_filter,
            **additional_kwargs
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

    return stt_local_model is not None


def is_whisper_lock():
    """
    Check if the Whisper model is currently being loaded.

    Returns:
        bool: True if the Whisper model is being loaded, False otherwise.
    """
    return stt_model_loading_thread_lock.locked()
