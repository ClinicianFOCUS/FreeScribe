
import ctypes
import os
import sys
import fcntl
from typing import List, Optional, Tuple
from Xlib import display, X, error
from Xlib.protocol import event as xlib_event


# Define the mutex name and error code
MUTEX_NAME = 'Global\\FreeScribe_Instance'
ERROR_ALREADY_EXISTS = 183
LINUX_LOCK_PATH = '/tmp/FreeScribe.lock'

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
        try:
            # Create or open the lock file
            mutex = open(LINUX_LOCK_PATH, 'w')
            # Try to acquire the lock
            fcntl.lockf(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # If we get here, no other instance is running
            return False

        except IOError:
            # Another instance has the lock
            return True
    else:
        raise RuntimeError('Unsupported platform')


def bring_to_front(app_name: str):
    """
    Bring the window with the given handle to the front.
    Parameters:
        app_name (str): The name of the application window to bring to the front
    """

    # TODO - Check platform and handle for different platform
    if sys.platform == 'linux':
        xdo = XDoToolPython()
        windows = xdo.search_window(app_name)
        xdo.activate_window(windows[0][0])
    else:
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
            os.remove(LINUX_LOCK_PATH)
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


class XDoToolPython:
    def __init__(self):
        self.display = display.Display()
        self.root = self.display.screen().root
        self.NET_WM_NAME = self.display.intern_atom('_NET_WM_NAME')
        self.WM_NAME = self.display.intern_atom('WM_NAME')
        self.NET_ACTIVE_WINDOW = self.display.intern_atom('_NET_ACTIVE_WINDOW')
        self.NET_WM_STATE = self.display.intern_atom('_NET_WM_STATE')
        self.NET_WM_STATE_FOCUSED = self.display.intern_atom('_NET_WM_STATE_FOCUSED')

    def get_window_name(self, window) -> Optional[str]:
        """Get window name using multiple property methods"""
        try:
            net_wm_name = window.get_full_property(self.NET_WM_NAME, 0)
            if net_wm_name:
                return net_wm_name.value.decode('utf-8')

            wm_name = window.get_full_property(self.WM_NAME, 0)
            if wm_name:
                return wm_name.value.decode('latin1')

            return None
        except error.XError:
            return None

    def search_window(self, pattern: str) -> List[Tuple[int, str]]:
        """Search for windows matching the pattern"""

        def recursive_search(window, pattern) -> List[Tuple[int, str]]:
            results = []
            try:
                name = self.get_window_name(window)
                if name and pattern.lower() in name.lower():
                    results.append((window.id, name))

                children = window.query_tree().children
                for child in children:
                    results.extend(recursive_search(child, pattern))
            except error.XError:
                pass
            return results

        return recursive_search(self.root, pattern)

    def activate_window(self, window_id: int) -> bool:
        """
        Activate (focus) a window by its ID using EWMH standards
        Returns True if successful, False otherwise
        """
        try:
            window = self.display.create_resource_object('window', window_id)

            # Send _NET_ACTIVE_WINDOW message
            event_data = [
                X.CurrentTime,  # Timestamp
                0,  # Currently active window (0 = none)
                0,  # Source indication (0 = application)
                0,  # Message data
                0  # Message data
            ]

            event_mask = (X.SubstructureRedirectMask | X.SubstructureNotifyMask)

            evt = xlib_event.ClientMessage(
                window=window,
                client_type=self.NET_ACTIVE_WINDOW,
                data=(32, event_data)
            )

            # Send the event to the root window
            self.root.send_event(evt, event_mask=event_mask)

            # Try to raise the window
            try:
                window.configure(stack_mode=X.Above)
            except error.BadMatch:
                # Some windows don't support being raised, ignore this error
                pass

            # Make sure changes are applied
            self.display.sync()
            return True

        except error.XError as e:
            print(f"Error activating window: {e}")
            return False