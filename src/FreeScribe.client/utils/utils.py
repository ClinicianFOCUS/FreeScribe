
import ctypes
import os
import sys
from filelock import FileLock

LOCK_FILE_PATH = "/tmp/myapp.lock" if sys.platform == "darwin" else "C:\\Temp\\myapp.lock"

# Define the mutex name and error code
MUTEX_NAME = 'Global\\FreeScribe_Instance'
ERROR_ALREADY_EXISTS = 183

# Global variable to store the mutex handle
mutex = None

lock = None

def _lock_file():
    global lock
    lock = FileLock(LOCK_FILE_PATH)
    print("Acquiring lock...")
    try :
        lock.acquire(timeout=1)
        print("Lock acquired.")
    except Exception as e:
        print(f"Error accessing lock file: {e}")
        print("Another instance is already running.")
        bring_to_front("AI Medical Scribe")
        sys.exit(1)


# function to check if another instance of the application is already running
def window_has_running_instance() -> bool:
    """
    Check if another instance of the application is already running.
    Returns:
        bool: True if another instance is running, False otherwise
    """
    if sys.platform == 'win32':
        global mutex

        # Create a named mutex
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
        return ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS
    elif sys.platform == 'darwin':
        _lock_file()

def bring_to_front(app_name: str):
    """
    Bring the window with the given handle to the front.
    Parameters:
        app_name (str): The name of the application window to bring to the front
    """

    if sys.platform == 'win32':
        U32DLL = ctypes.WinDLL('user32')
        SW_SHOW = 5
        hwnd = U32DLL.FindWindowW(None, app_name)
        U32DLL.ShowWindow(hwnd, SW_SHOW)
        U32DLL.SetForegroundWindow(hwnd)
    elif sys.platform == 'darwin':
        from AppKit import NSApplication, NSApp
        app = NSApplication.sharedApplication()
        app.activateIgnoringOtherApps_(True)
        for window in app.windows():
            if window.title() == app_name:
                window.makeKeyAndOrderFront_(None)
                break

def close_mutex():
    """
    Close the mutex handle to release the resource.
    """
    global mutex
    if mutex:
        ctypes.windll.kernel32.ReleaseMutex(mutex)
        ctypes.windll.kernel32.CloseHandle(mutex)
        mutex = None

def on_exit():
    """
    Function to be called when the application exits.
    """
    # This function will be called when the application closes
    if sys.platform == 'win32':
        close_mutex()
    elif sys.platform == 'darwin':
        if os.path.exists(LOCK_FILE_PATH):
            os.remove(LOCK_FILE_PATH)
        print("Lock file removed.")
