"""
Logging Configuration
Centralized logging setup for the application.
"""

import logging
import logging.config
import sys
from pathlib import Path
from .config import get_settings


def setup_logging():
    """Setup application logging configuration"""
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': settings.log_level,
                'formatter': 'default',
                'stream': sys.stdout
            }
        },
        'loggers': {
            '': {  # Root logger
                'level': settings.log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'app': {
                'level': settings.log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'fastapi': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            }
        }
    }
    
    # Add file handler if log file is specified
    if settings.log_file:
        config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': settings.log_level,
            'formatter': 'detailed',
            'filename': settings.log_file,
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5
        }
        
        # Add file handler to loggers
        for logger_name in config['loggers']:
            config['loggers'][logger_name]['handlers'].append('file')
    
    # Configure logging
    logging.config.dictConfig(config)
    
    # Get logger for this module
    logger = logging.getLogger(__name__)
    logger.info("Logging configuration completed")
    logger.info(f"Log level: {settings.log_level}")
    if settings.log_file:
        logger.info(f"Log file: {settings.log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)