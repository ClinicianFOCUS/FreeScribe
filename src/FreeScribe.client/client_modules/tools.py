import ctypes
import os
from pathlib import Path

from UI.SettingsConstant import Architectures, SettingsKeys
from client_modules.app_context import AppContext
from utils.file_utils import get_file_path

from utils.log_config import logger


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


def set_cuda_paths():
    """
    Configure CUDA-related environment variables and paths.

    Sets up the necessary environment variables for CUDA execution when CUDA
    architecture is selected. Updates CUDA_PATH, CUDA_PATH_V12_4, and PATH
    environment variables with the appropriate NVIDIA driver paths.
    """
    if (get_selected_whisper_architecture() != Architectures.CUDA.architecture_value) or (
            AppContext.app_settings.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value] != Architectures.CUDA.label):
        return

    nvidia_base_path = Path(get_file_path('nvidia-drivers'))

    cuda_path = nvidia_base_path / 'cuda_runtime' / 'bin'
    cublas_path = nvidia_base_path / 'cublas' / 'bin'
    cudnn_path = nvidia_base_path / 'cudnn' / 'bin'

    paths_to_add = [str(cuda_path), str(cublas_path), str(cudnn_path)]
    env_vars = ['CUDA_PATH', 'CUDA_PATH_V12_4', 'PATH']

    for env_var in env_vars:
        current_value = os.environ.get(env_var, '')
        new_value = os.pathsep.join(paths_to_add + ([current_value] if current_value else []))
        os.environ[env_var] = new_value


def get_selected_whisper_architecture():
    """
    Determine the appropriate device architecture for the Whisper model.

    Returns:
        str: The architecture value (CPU or CUDA) based on user settings.
    """
    device_type = Architectures.CPU.architecture_value
    if AppContext.app_settings.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value] == Architectures.CUDA.label:
        device_type = Architectures.CUDA.architecture_value

    return device_type
