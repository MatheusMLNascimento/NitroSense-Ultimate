"""
Professional logging configuration for NitroSense Ultimate.
Implements rotating file handler with structured logging.
"""

import logging
import logging.handlers
import sys
import gzip
import shutil
from pathlib import Path
from .constants import LOG_CONFIG


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Rotating file handler with gzip compression for old logs."""

    def doRollover(self):
        """Perform rollover with compression."""
        super().doRollover()
        # Compress the backup file
        if self.backupCount > 0:
            for i in range(self.backupCount, 0, -1):
                backup_file = f"{self.baseFilename}.{i}"
                if Path(backup_file).exists():
                    compressed_file = f"{backup_file}.gz"
                    with open(backup_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    Path(backup_file).unlink()  # Remove uncompressed backup
                    logger.debug(f"Compressed log: {compressed_file}")


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
    Configure professional logging with both file and console handlers.
    
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
    
    # File handler with rotation and compression
    file_handler = CompressedRotatingFileHandler(
        log_file,
        maxBytes=LOG_CONFIG["max_size"],
        backupCount=LOG_CONFIG["backup_count"],
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Formatters
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt=LOG_CONFIG["date_format"],
    )
    console_formatter = ColoredFormatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt=LOG_CONFIG["date_format"],
    )
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Global logger instance
logger = setup_logging("NitroSense")
