import logging
import os
from datetime import datetime


def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = './logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Get current date for creating the log file name
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'app_{current_date}.log')

    # Configure logging to write to the current day's log file
    logging.basicConfig(
        filename=log_file,
        filemode='a',  # append mode
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )
