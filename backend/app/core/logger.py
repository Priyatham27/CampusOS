import logging
import sys
from app.core.config import settings

def setup_logger():
    logger = logging.getLogger("campusos")
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Check if handler is already added to prevent duplicates
    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

logger = setup_logger()
