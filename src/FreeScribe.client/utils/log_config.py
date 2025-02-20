import os
import sys
from collections import deque
from logging.handlers import RotatingFileHandler
import logging
import traceback
from utils.file_utils import get_resource_path


class SafeStreamHandler(logging.StreamHandler):
    """A safe stream handler that checks stream state before operations.
    
    This handler extends logging.StreamHandler to prevent errors when
    working with potentially closed streams.
    """
    def emit(self, record):
        """Emit a record if the stream is open.
        
        :param record: The log record to emit
        :type record: logging.LogRecord
        """
        if self.stream and not self.stream.closed:
            super().emit(record)

    def close(self):
        """Close the handler only if the stream is open.
        
        Prevents errors when closing already-closed streams.
        """
        if self.stream and not self.stream.closed:  # Only close if open
            super().close()


class BufferHandler(logging.Handler):
    """A custom logging handler that writes log messages to the TrioOutput buffer.
    
    This handler captures log records and writes them to an in-memory buffer
    maintained by the TripleOutput class.
    """
    MAX_BUFFER_SIZE = 2500  # Maximum number of lines in the buffer
    buffer = deque(maxlen=MAX_BUFFER_SIZE)

    def emit(self, record):
        """Emit a record by writing it to the TrioOutput buffer.

        :param record: The log record to be written
        :type record: logging.LogRecord
        :note: Any exceptions during emission are handled by the parent class's handleError method
        """
        try:
            msg = self.format(record)
            BufferHandler.buffer.append(msg)
        except Exception:
            self.handleError(record)

    @staticmethod
    def get_buffer_content():
        """Retrieve all content stored in the buffer.

        :return: The complete buffer contents as a single string with newline separators
        :rtype: str
        :note: The buffer maintains a fixed size (MAX_BUFFER_SIZE) and automatically
               discards oldest entries when full
        """
        return '\n'.join(BufferHandler.buffer)


class TripleOutput:
    def __init__(self, log_func):
        """Initialize the triple output handler.

        :param log_func: The logging function to use for output (e.g., logger.info)
        :type log_func: callable
        """
        self.log_func = log_func

    def write(self, message):
        """Write a message to the buffer, original stdout, and log file.

        :param message: The message to be written
        :type message: str
        :note: 
            - Empty messages are ignored
            - Multi-line messages are split and written line by line
        """
        try:
            message = message.strip()
            if not message:
                return
            for line in message.splitlines():
                self.log_func(line)
        except Exception as e:
            err = traceback.format_exc()
            out = sys.__stderr__ or sys.__stdout__
            if not out:
                return
            out.write(str(e) + '\n')
            out.write(err)

    def flush(self):
        pass


# Define custom level
DIAGNOSE_LEVEL = 99
logging.addLevelName(DIAGNOSE_LEVEL, "DIAG")
# Configure logging
if os.environ.get("FREESCRIBE_DEBUG"):
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO
LOG_FILE_NAME = get_resource_path("freescribe.log")
# 10 MB
LOG_FILE_MAX_SIZE = 10 * 1024 * 1024
# Keep up to 1 backup log files
LOG_FILE_BACKUP_COUNT = 1
LOG_FORMAT = '[%(asctime)s] | %(levelname)s | %(name)s | %(threadName)s | [%(filename)s:%(lineno)d in %(funcName)s] | %(message)s'

formatter = logging.Formatter(LOG_FORMAT)

# When running a PyInstaller-built application with --windowed mode, there's no console,
# so sys.stdout and sys.stderr are set to None.
# Since Python's logging module tries to write to sys.stdout (or another stream handler),
# it fails with AttributeError: 'NoneType' object has no attribute 'write'.
if sys.stderr or sys.stdout:
    console_handler = SafeStreamHandler(sys.stderr or sys.stdout)
else:
    console_handler = logging.NullHandler()
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(formatter)

file_handler = RotatingFileHandler(LOG_FILE_NAME, maxBytes=LOG_FILE_MAX_SIZE, backupCount=LOG_FILE_BACKUP_COUNT)
file_handler.setLevel(LOG_LEVEL)
file_handler.setFormatter(formatter)

buffer_handler = BufferHandler()
buffer_handler.setLevel(LOG_LEVEL)
buffer_handler.setFormatter(formatter)

# root logger settings
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[console_handler, file_handler, buffer_handler],
    format=LOG_FORMAT
)
logger = logging.getLogger("freescribe")
logger.setLevel(LOG_LEVEL)

sys.stdout = TripleOutput(logger.info)
sys.stderr = TripleOutput(lambda msg: logger.log(DIAGNOSE_LEVEL, msg))
