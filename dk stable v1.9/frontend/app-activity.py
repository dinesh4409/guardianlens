import time
import win32gui
import win32process
import psutil
import requests
import datetime
import logging
import sys
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).resolve().parent
SERVER_URL = "http://127.0.0.1:2000/app-activity"
POLL_INTERVAL = 2  # Check active window every 2 seconds

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def get_active_window_info():
    """Get the title and executable name of the active window."""
    try:
        window = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(window)
        
        _, pid = win32process.GetWindowThreadProcessId(window)
        process = psutil.Process(pid)
        executable = process.name()
        
        return title, executable
    except Exception as e:
        # logging.debug(f"Error getting window info: {e}")
        return None, None

def main():
    logging.info("Starting App Activity Tracker...")
    last_window = None
    start_time = time.time()
    
    try:
        while True:
            title, executable = get_active_window_info()
            current_window = (title, executable)
            
            if current_window != last_window:
                if last_window:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # Only report if it was active for more than 1 second
                    if duration > 1:
                        payload = {
                            "app": last_window[1],
                            "title": last_window[0],
                            "duration": round(duration, 2),
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        try:
                            r = requests.post(SERVER_URL, json=payload, timeout=5)
                            logging.info(f"Recorded: {last_window[1]} ({round(duration, 1)}s) | Server: {r.status_code}")
                        except Exception as e:
                            logging.error(f"Failed to send data: {e}")
                
                last_window = current_window
                start_time = time.time()
            
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        logging.info("App Activity Tracker stopped by user.")
    except Exception as e:
        logging.error(f"Critical error: {e}")

if __name__ == "__main__":
    main()
