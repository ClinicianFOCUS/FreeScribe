import ctypes
import os
import sys

def get_file_path(*file_names: str) -> str:
  """
  Get the full path to a files. Use Temporary directory at runtime for bundled apps, otherwise use the current working directory.

  :param file_names: The names of the directories and the file.
  :type file_names: str
  :return: The full path to the file.
  :rtype: str
  """
  base = _get_base_path(use_programdata=False)
  return os.path.join(base, *file_names)  

def _get_programdata_path() -> str:
    """
    Get the path to the ProgramData directory using ctypes.
    """
    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.shell32.SHGetFolderPathW(None, 0x23, None, 0, buf)
    return buf.value

def _get_base_path(use_programdata: bool) -> str:
    if hasattr(sys, '_MEIPASS'):
        return _get_programdata_path() if use_programdata else sys._MEIPASS
    return os.path.abspath(".")

def get_resource_path(filename: str) -> str:
    """
    Get the path to the files. Use ProgramData for bundled apps, otherwise use the current working directory.

    :param filename: The name of the file.
    :type filename: str
    :return: The full path to the file.
    :rtype: str
    """
    base = _get_base_path(use_programdata=False)
    return os.path.join(base, 'FreeScribe', filename)
