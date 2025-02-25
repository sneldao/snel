import logging
import sys
from typing import Any

# Monkey patch FileHandler to prevent file creation
class NoFileHandler(logging.Handler):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__()
    
    def emit(self, record: logging.LogRecord) -> None:
        pass

# Replace FileHandler with our no-op version
original_file_handler = logging.FileHandler
logging.FileHandler = NoFileHandler  # type: ignore

# Configure root logger before any imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True  # This will override any existing logger configuration
)

# Create a NullHandler that will be used as a fallback
null_handler = logging.NullHandler()

# Configure the dowse logger to use stdout
dowse_logger = logging.getLogger('dowse')
dowse_logger.handlers = []  # Remove any existing handlers
dowse_logger.addHandler(logging.StreamHandler(sys.stdout))
dowse_logger.addHandler(null_handler)  # Add null handler as fallback
dowse_logger.propagate = False  # Prevent duplicate logs

# Also configure eth-rpc logger since it's used by dowse
eth_rpc_logger = logging.getLogger('eth_rpc')
eth_rpc_logger.handlers = []
eth_rpc_logger.addHandler(logging.StreamHandler(sys.stdout))
eth_rpc_logger.addHandler(null_handler)
eth_rpc_logger.propagate = False 