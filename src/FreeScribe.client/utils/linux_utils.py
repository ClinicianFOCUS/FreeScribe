"""
Linux-specific utilities for process and window management.
"""
import utils.system
if utils.system.is_linux():
    import logging
    import os
    import fcntl
    import tempfile
    from typing import Optional, Tuple, List

    from Xlib import display, error, X
    from Xlib.protocol import event as xlib_event

    logger = logger.getLogger(__name__)

    # Lock file path for Linux - use temp directory which is guaranteed to exist and be writable
    LINUX_LOCK_PATH = os.path.join(tempfile.gettempdir(), f'FreeScribe_{os.getuid()}.lock')

    def check_instance() -> Tuple[Optional[object], bool]:
        """
        Check if another instance is running using a lock file on Linux.
        
        Returns:
            Tuple[Optional[object], bool]: A tuple containing:
                - The lock file object if successful, None otherwise
                - True if another instance is running, False otherwise
        """
        try:
            # First try to read the existing lock file
            try:
                with open(LINUX_LOCK_PATH, 'r') as f:
                    pid = int(f.read().strip())
                    try:
                        os.kill(pid, 0)  # Check if process exists
                        return None, True
                    except OSError:
                        # Process is not running, we can take over
                        os.remove(LINUX_LOCK_PATH)
            except (IOError, ValueError):
                pass  # File doesn't exist or is invalid, we can create it

            # Create or open the lock file
            lock_file = open(LINUX_LOCK_PATH, 'w')
            # Try to acquire an exclusive lock
            fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Write the current process ID to the file
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            return lock_file, False
        except IOError:
            return None, True

    def cleanup_lock(lock_file: object) -> None:
        """
        Clean up the lock file when the application exits.
        
        Args:
            lock_file: The lock file object to clean up
        """
        try:
            if lock_file:
                fcntl.lockf(lock_file, fcntl.F_UNLCK)
                lock_file.close()
                if os.path.exists(LINUX_LOCK_PATH):
                    os.remove(LINUX_LOCK_PATH)
        except Exception as e:
            logger.error(f"Error cleaning up lock file: {e}")

    def bring_to_front(app_name: str) -> bool:
        """
        Bring the window with the given name to the front on Linux.
        
        Args:
            app_name (str): The name of the application window to bring to the front
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            xdo = XDoToolPython()
            windows = xdo.search_window(app_name)
            xdo.activate_window(windows[0][0])
            return True
        except Exception as e:
            logger.error(f"Failed to bring window to front: {e}")
            return False


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
                if net_wm_name:= window.get_full_property(self.NET_WM_NAME, 0):
                    return net_wm_name.value.decode('utf-8')

                if wm_name:= window.get_full_property(self.WM_NAME, 0):
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
