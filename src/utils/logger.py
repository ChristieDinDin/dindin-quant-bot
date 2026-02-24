"""
Logging configuration and utilities.

Provides consistent logging across the entire application.
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from .config import LoggingConfig


class Logger:
    """
    Application logger with file and console output.
    """
    
    _loggers = {}
    _configured = False
    
    @classmethod
    def configure(cls, config: LoggingConfig) -> None:
        """
        Configure logging system.
        
        Args:
            config: LoggingConfig instance
        """
        if cls._configured:
            return
        
        # Create logs directory
        if config.file_path:
            log_dir = Path(config.file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set root logger level
        logging.root.setLevel(getattr(logging, config.level))
        
        # Create formatters
        formatter = logging.Formatter(config.format)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, config.level))
        console_handler.setFormatter(formatter)
        
        # Add console handler to root logger
        logging.root.addHandler(console_handler)
        
        # File handler (rotating)
        if config.file_path:
            file_handler = logging.handlers.RotatingFileHandler(
                config.file_path,
                maxBytes=config.max_bytes,
                backupCount=config.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, config.level))
            file_handler.setFormatter(formatter)
            logging.root.addHandler(file_handler)
        
        cls._configured = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Logger instance
        """
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        
        return cls._loggers[name]


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger.
    
    Usage:
        from src.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return Logger.get_logger(name)


# Context manager for temporary log level changes
class temporary_log_level:
    """
    Context manager to temporarily change log level.
    
    Usage:
        with temporary_log_level(logging.DEBUG):
            # Debug logging enabled here
            logger.debug("Detailed info")
        # Back to original level
    """
    
    def __init__(self, level: int):
        self.level = level
        self.original_level = None
    
    def __enter__(self):
        self.original_level = logging.root.level
        logging.root.setLevel(self.level)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.root.setLevel(self.original_level)
