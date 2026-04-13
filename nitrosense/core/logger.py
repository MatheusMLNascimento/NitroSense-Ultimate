"""
Professional logging configuration for NitroSense Ultimate.
Implements rotating file handler with structured logging and batch writing.

CRITICAL DESIGN PRINCIPLES:
1. Rotating logs—max 5MB per file, compress old logs with gzip
2. Batch writing—accumulate logs for 30s, then flush to disk
3. Minimize I/O—reduces SSD wear on long-running sessions
4. Structured logging—Module, Function, Line, Action, Cause
"""

import logging
import logging.handlers
import sys
import gzip
import shutil
import time
from pathlib import Path
from threading import Lock
from collections import deque
from .constants import LOG_CONFIG


class BatchedFileHandler(logging.handlers.RotatingFileHandler):
    """
    Rotating file handler with batched writing for I/O efficiency.
    Accumulates log records in memory, flushing every 30s or on full batch.
    """

    def __init__(self, *args, batch_size: int = 50, batch_timeout: float = 30.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batch_buffer = deque()
        self.last_flush_time = time.time()
        self.batch_lock = Lock()

    def emit(self, record):
        """Emit record to batch buffer instead of directly to file."""
        try:
            msg = self.format(record)
            
            with self.batch_lock:
                self.batch_buffer.append(msg)
                
                # Flush if batch is full or timeout expired
                elapsed = time.time() - self.last_flush_time
                if len(self.batch_buffer) >= self.batch_size or elapsed >= self.batch_timeout:
                    self._flush_batch()
        except Exception:
            self.handleError(record)

    def _flush_batch(self):
        """Write accumulated batch to file."""
        if not self.batch_buffer:
            return
        
        try:
            with open(self.baseFilename, 'a', encoding='utf-8') as f:
                while self.batch_buffer:
                    msg = self.batch_buffer.popleft()
                    f.write(msg + '\n')
            
            # Check if rollover needed
            if self.baseFilename and self.maxBytes > 0:
                if Path(self.baseFilename).stat().st_size >= self.maxBytes:
                    self.doRollover()
            
            self.last_flush_time = time.time()
        except Exception as e:
            logging.error(f"Batch flush failed: {e}")

    def close(self):
        """Ensure batch is flushed before closing."""
        self._flush_batch()
        super().close()

    def flush(self):
        """Flush batch to file."""
        with self.batch_lock:
            self._flush_batch()
        super().flush()


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Rotating file handler with gzip compression for old logs."""

    def doRollover(self):
        """Perform rollover with automatic compression of old logs."""
        super().doRollover()
        # Compress the backup file
        if self.backupCount > 0:
            for i in range(self.backupCount, 0, -1):
                backup_file = f"{self.baseFilename}.{i}"
                if Path(backup_file).exists():
                    compressed_file = f"{backup_file}.gz"
                    try:
                        with open(backup_file, 'rb') as f_in:
                            with gzip.open(compressed_file, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        Path(backup_file).unlink()  # Remove uncompressed backup
                    except Exception as e:
                        logging.debug(f"Failed to compress log: {e}")


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging(name=__name__, log_level=LOG_CONFIG["log_level"]):
    """
    Configure professional logging with file rotation, compression, and batch writing.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create log directory
    log_dir = Path(LOG_CONFIG["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / LOG_CONFIG["log_file"]
    
    # File handler with batched writing for I/O efficiency
    file_handler = BatchedFileHandler(
        log_file,
        maxBytes=LOG_CONFIG.get("max_size", 5242880),  # 5MB default
        backupCount=LOG_CONFIG.get("backup_count", 5),
        batch_size=50,  # Flush after 50 messages
        batch_timeout=30.0,  # Or after 30 seconds
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Formatters
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt=LOG_CONFIG.get("date_format", "%Y-%m-%d %H:%M:%S"),
    )
    console_formatter = ColoredFormatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt=LOG_CONFIG.get("date_format", "%Y-%m-%d %H:%M:%S"),
    )
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Global logger instance
logger = setup_logging("NitroSense")
