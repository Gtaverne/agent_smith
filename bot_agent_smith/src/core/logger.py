import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style

# Initialize colorama for cross-platform color support
init()

class ColorFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Add color to level name if outputting to console
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)

def setup_logger(name="agent_smith"):
    """Setup and return the logger instance"""
    # Create logger
    logger = logging.getLogger(name)
    
    # Get log level from environment variable, default to INFO
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    level = getattr(logging, log_level, logging.INFO)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler with color formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = '[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d] %(message)s'
    console_handler.setFormatter(ColorFormatter(console_format))
    
    # Create file handler
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(
        logs_dir / f"agent_smith_{timestamp}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = '[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d] %(message)s'
    file_handler.setFormatter(logging.Formatter(file_format))
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Create and expose the global logger instance
logger = setup_logger()

# Convenience methods
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical