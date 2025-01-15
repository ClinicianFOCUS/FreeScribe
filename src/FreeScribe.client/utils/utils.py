
import ctypes
import os
import sys
import fcntl

# Define the mutex name and error code
MUTEX_NAME = 'Global\\FreeScribe_Instance'
ERROR_ALREADY_EXISTS = 183

# Global variable to store the mutex handle
mutex = None

# function to check if another instance of the application is already running
def window_has_running_instance() -> bool:
    """
    Check if another instance of the application is already running.
    Returns:
        bool: True if another instance is running, False otherwise
    """
    global mutex

    if sys.platform == 'win32':
        # Create a named mutex
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
        return ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS
    elif sys.platform == 'linux':
        lock_file_path = '/tmp/FreeScribe.lock'

        try:
            # Create or open the lock file
            mutex = open(lock_file_path, 'w')

            # Try to acquire the lock
            fcntl.lockf(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # If we get here, no other instance is running
            return False

        except IOError:
            # Another instance has the lock
            return True
        except Exception as e:
            # Handle any other errors
            print(f"Error checking for running instance: {e}")
            return False
    else:
        raise RuntimeError('Unsupported platform')


def bring_to_front(app_name: str):
    """
    Bring the window with the given handle to the front.
    Parameters:
        app_name (str): The name of the application window to bring to the front
    """

    # TODO - Check platform and handle for different platform
    U32DLL = ctypes.WinDLL('user32')
    SW_SHOW = 5
    hwnd = U32DLL.FindWindowW(None, app_name)
    U32DLL.ShowWindow(hwnd, SW_SHOW)
    U32DLL.SetForegroundWindow(hwnd)


def cleanup_lock():
    """
    Cleanup function to release the lock file when the application exits.
    Should be called when the application is shutting down.
    """
    global mutex
    if sys.platform == 'linux' and mutex is not None:
        try:
            fcntl.lockf(mutex, fcntl.LOCK_UN)
            mutex.close()
            os.remove(mutex.name)
        except Exception as e:
            print(f"Error cleaning up lock file: {e}")


def close_mutex():
    """
    Close the mutex handle to release the resource.
    """
    global mutex
    if not mutex:
        return
    if sys.platform == 'linux':
        cleanup_lock()
    else:
        ctypes.windll.kernel32.ReleaseMutex(mutex)
        ctypes.windll.kernel32.CloseHandle(mutex)
    mutex = None
