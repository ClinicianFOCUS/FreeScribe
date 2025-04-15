import ctypes
from functools import lru_cache
import os
import sys


APP_NAME = 'FreeScribe'

def is_flatpak():
    return sys.platform.startswith('linux') and os.environ.get('container') == 'flatpak'


def _flatpak_init():
    config_path = _get_flatpak_data_dir()
    if not os.path.exists(config_path):
        os.makedirs(config_path, exist_ok=True)
    # soft link data {assets, markdown, models} so app can visit them
    for fname in ['assets', 'markdown', 'models', 'whisper-assets', '__version__']:
        target = os.path.join(config_path, fname)
        if os.path.islink(target):
            continue
        # source, link_name
        os.symlink(os.path.join('/app/lib/python3.10/site-packages/FreeScribe_client/', fname), target)
    

def get_file_path(*file_names: str) -> str:
    """
    Get the full path to a files. Use Temporary directory at runtime for bundled apps, otherwise use the current working directory.

    :param file_names: The names of the directories and the file.
    :type file_names: str
    :return: The full path to the file.
    :rtype: str
    """
    if is_flatpak():
        return os.path.join(_get_flatpak_data_dir(), *file_names)
    base = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.abspath('.')
    return os.path.join(base, *file_names)


def get_resource_path(filename: str, shared: bool = False) -> str:
    """
    Get the path to the files. Use User data directory for bundled apps, otherwise use the current working directory.

    :param filename: The name of the file.
    :param shared: Whether to use the shared directory.
    :type filename: str
    :return: The full path to the file.
    :rtype: str
    """
    if is_flatpak():
        return os.path.join(_get_flatpak_data_dir(), filename)
    if not hasattr(sys, '_MEIPASS'):
        return os.path.abspath(filename)
    base = _get_user_data_dir(shared)
    freescribe_dir = os.path.join(base, 'FreeScribe')

    # Check if the FreeScribe directory exists, if not, create it
    try:
        if not os.path.exists(freescribe_dir):
            os.makedirs(freescribe_dir)
    except OSError as e:
        raise RuntimeError(f"Failed to create FreeScribe directory: {e}") from e

    return os.path.join(freescribe_dir, filename)


def _get_user_data_dir(shared: bool = False) -> str:
    """
    Get the user data directory for the current platform.

    :param shared: Whether to use the shared directory.
    :return: The path to the user data directory.
    :rtype: str
    """
    if sys.platform == "win32": # Windows
        buf = ctypes.create_unicode_buffer(1024)
        ctypes.windll.shell32.SHGetFolderPathW(None, 0x001a, None, 0, buf)
        return buf.value
    elif sys.platform == "darwin": # macOS
        return "/Users/Shared/" if shared else os.path.expanduser("~/Library/Application Support")
    else: # Linux
        path = os.environ.get("XDG_DATA_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.local/share")
        return path


def _get_flatpak_data_dir():
    return os.path.join(_get_user_data_dir(), APP_NAME)

if is_flatpak():
    _flatpak_init()
