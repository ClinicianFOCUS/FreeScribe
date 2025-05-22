"""
macOS-specific utilities for process and window management.
"""
import logging
import os
import utils.system
if utils.system.is_linux() or utils.system.is_macos():
    import fcntl

from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Lock file path for macOS
if utils.system.is_macos():
    MACOS_LOCK_PATH = f'/tmp/FreeScribe_{os.getuid()}.lock'
else:
    MACOS_LOCK_PATH = '/tmp/FreeScribe.lock'

def check_instance() -> Tuple[Optional[object], bool]:
    """
    Check if another instance is running using a lock file on macOS.
    
    Returns:
        Tuple[Optional[object], bool]: A tuple containing:
            - The lock file object if successful, None otherwise
            - True if another instance is running, False otherwise
    """
    try:
        lock_file = open(MACOS_LOCK_PATH, 'w')
        fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file, False
    except IOError:
        return None, True

def cleanup_lock(lock_file: object) -> None:
    """
    Clean up the lock file on macOS.
    
    Args:
        lock_file: The lock file object to clean up
    """
    if lock_file:
        try:
            fcntl.lockf(lock_file, fcntl.LOCK_UN)
            lock_file.close()
            os.remove(MACOS_LOCK_PATH)
        except Exception as e:
            logger.exception(f"Error cleaning up lock file: {e}")

def bring_to_front(app_name: str) -> bool:
    """
    Bring the window with the given name to the front on macOS.
    
    Args:
        app_name (str): The name of the application window to bring to the front
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # TODO: Implement macOS window activation using AppleScript or other macOS-specific APIs
        # This is a placeholder for future implementation
        logger.warning("Window activation not yet implemented for macOS")
        return False
    except Exception as e:
        logger.error(f"Failed to bring window to front: {e}")
        return False 