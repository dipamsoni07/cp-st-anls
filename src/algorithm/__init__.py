import os
import sys
import coloredlogs
from dotenv import load_dotenv
import pytz
from datetime import datetime
import logging


IST = pytz.timezone('Asia/Kolkata')
def ist_time(*args):
    return datetime.now(IST).timetuple()
logging.Formatter.converter = ist_time  

def get_logger(name:str, isin:str = None) -> logging.Logger:
    """
    Returns a loggre configured with:
        - A file handler writing to a file named based on the module's name.
        - A console handler only for the specific modules to display on console.
    """
    
    if isin:
        log_dir = f"logs/{datetime.now().strftime('%Y-%m-%d')}/{isin}/"
    else:
        log_dir = f"logs/{datetime.now().strftime('%Y-%m-%d')}/"
    os.makedirs(log_dir, exist_ok=True)
    
    logger_name = f"{name}-{isin}" if isin else name
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    logger.propagate = False # to avoid duplicate logs.
    
    formatter = logging.Formatter("[%(asctime)s: %(levelname)s: %(module)s]: %(message)s")
    fmt_str = "[%(asctime)s: %(levelname)s: %(module)s]: %(message)s"
    # coloredlogs.install(level="INFO", logger=logger, fmt=fmt_str)

    # Each module with separate log file...
    module_filename = name.split('.')[-1]
    log_filename = os.path.join(log_dir, f"{module_filename[:15].upper()}#{datetime.now().strftime('%H;%M;%S')}.log")
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    
    stream_module_logs_to_console = [
        'main'
        # 'src.algorithm.core.signal_based_order_manager',
        # 'src.algorithm.algo_core.algo',
    ]
    
    # if False:
    if name in stream_module_logs_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # console_handler.addFilter(AlgoConsoleFilter)
        logger.addHandler(console_handler)
    
    return logger
    
    

logger = logging.getLogger("algorithm")

