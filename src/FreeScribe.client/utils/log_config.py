import os
import sys
from collections import deque
from logging.handlers import RotatingFileHandler
import logging
from utils.file_utils import get_resource_path


class BufferHandler(logging.Handler):
    """
    A custom logging handler that writes log messages to the TrioOutput buffer.
    """
    def emit(self, record):
        """Emit a record by writing it to the TrioOutput buffer.

        Args:
            record (logging.LogRecord): The log record to be written

        Note:
            Any exceptions during emission are handled by the parent class's handleError method
        """
        try:
            msg = self.format(record)
            TripleOutput.buffer.append(msg)
        except Exception:
            self.handleError(record)


class TripleOutput:
    MAX_BUFFER_SIZE = 2500  # Maximum number of lines in the buffer
    buffer = deque(maxlen=MAX_BUFFER_SIZE)

    def __init__(self, log_func):
        """Initialize the triple output handler.

        Args:
            logger (logging.Logger): The logger instance to use for logging
            level (int): The logging level to use for output

        Creates a deque buffer with a max length and stores references to original stdout/stderr streams.
        """
        # DualOutput.buffer = deque(maxlen=DualOutput.MAX_BUFFER_SIZE)  # Buffer with a fixed size
        self.original_stdout = sys.__stdout__  # Save the original stdout
        self.original_stderr = sys.__stderr__  # Save the original stderr
        self.log_func = log_func

    def write(self, message):
        """Write a message to the buffer, original stdout, and log file.

        Args:
            message (str): The message to be written

        Note:
            - Empty messages are ignored
            - Multi-line messages are split and written line by line
        """
        message = message.strip()
        if not message:
            return
        if '\n' in message:
            for line in message.split('\n'):
                self.log_func(line)
            return
        self.log_func(message)

    def flush(self):
        """Flush the original stdout to ensure output is written immediately.

        Note:
            This is required to maintain proper stream behavior and ensure
            output appears in real-time
        """
        if self.original_stdout is not None:
            self.original_stdout.flush()

    @staticmethod
    def get_buffer_content():
        """Retrieve all content stored in the buffer.

        Returns:
            str: The complete buffer contents as a single string with newline separators

        Note:
            The buffer maintains a fixed size (MAX_BUFFER_SIZE) and automatically
            discards oldest entries when full
        """
        return '\n'.join(TripleOutput.buffer)


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


formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(formatter)

file_handler = RotatingFileHandler(LOG_FILE_NAME, maxBytes=LOG_FILE_MAX_SIZE, backupCount=LOG_FILE_BACKUP_COUNT)
file_handler.setLevel(LOG_LEVEL)
file_handler.setFormatter(formatter)

buffer_handler = BufferHandler()
buffer_handler.setLevel(LOG_LEVEL)
buffer_handler.setFormatter(formatter)

logger = logging.getLogger("freescribe")
logger.setLevel(LOG_LEVEL)
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(buffer_handler)

triple = TripleOutput(logger.info)
sys.stdout = triple
sys.stderr = triple
