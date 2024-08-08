import os
import psutil
import mysql.connector
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timedelta
import time
import hashlib

# Custom event handler class for monitoring filesystem events
class MyHandler(FileSystemEventHandler):
    def __init__(self, db_config, user, device):
        # Establish a connection to the database
        self.conn = mysql.connector.connect(**db_config)
        self.cursor = self.conn.cursor()
        self.user = user
        self.device = device
        # List of system directories to exclude from monitoring
        self.system_dirs = [
            'C:\\Windows',
            'C:\\ProgramData',
            'C:\\Program Files',
            'C:\\Program Files (x86)',
            os.getenv('APPDATA'),
            os.getenv('LOCALAPPDATA')
        ]
        self.logged_events = set()  # Set to keep track of logged events to avoid duplicates
        self.open_files = set()  # Set to keep track of currently open files
        self.recently_opened_files = {}  # Dictionary to track recently opened files with timestamps
        self.recently_deleted_files = {}  # Dictionary to track recently deleted files with their hashes and deletion times

    # Method to log user activities into the database
    def log_activity(self, activity_type, details):
        # Get the current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        event_key = (activity_type, details, timestamp)
        # Log the event if it hasn't been logged already
        if event_key not in self.logged_events:
            query = "INSERT INTO user_activity (user, device, activity_type, details, timestamp) VALUES (%s, %s, %s, %s, %s)"
            values = (self.user, self.device, activity_type, details, timestamp)
            self.cursor.execute(query, values)
            self.conn.commit()
            self.logged_events.add(event_key)

    # Handler for modified files
    def on_modified(self, event):
        # Check if the path is not a system path and the event is not a directory
        if not self.is_system_path(event.src_path) and not event.is_directory:
            # Log the modification if the file was not recently opened
            if not self.was_recently_opened(event.src_path):
                self.log_activity("file_modified", event.src_path)

    # Handler for created files or directories
    def on_created(self, event):
        # Check if the path is not a system path
        if not self.is_system_path(event.src_path):
            if event.is_directory:
                # Log the creation of a directory
                self.log_activity("folder_created", event.src_path)
            else:
                # Get the hash of the created file
                file_hash = self.get_file_hash(event.src_path)
                # Handle possible move events by comparing file hashes
                self.handle_possible_move(event.src_path, file_hash)
                # Log the creation of a file
                self.log_activity("file_created", event.src_path)

    # Handler for deleted files or directories
    def on_deleted(self, event):
        # Check if the path is not a system path
        if not self.is_system_path(event.src_path):
            if event.is_directory:
                # Log the deletion of a directory
                self.log_activity("folder_deleted", event.src_path)
            else:
                # Get the hash of the deleted file
                file_hash = self.get_file_hash(event.src_path)
                # Track the recently deleted file with its hash and deletion time
                self.recently_deleted_files[event.src_path] = (file_hash, datetime.now())
                # Log the deletion of a file
                self.log_activity("file_deleted", event.src_path)

    # Handler for moved files
    def on_moved(self, event):
        # Check if the path is not a system path
        if not self.is_system_path(event.src_path):
            # Log the move event with source and destination paths
            self.log_activity("file_moved", f"from {event.src_path} to {event.dest_path}")

    # Check if the file was recently opened to avoid duplicate logging
    def was_recently_opened(self, file_path):
        if file_path in self.recently_opened_files:
            event_time = self.recently_opened_files[file_path]
            # Check if the file was opened within the last 10 seconds
            if (datetime.now() - event_time).seconds < 10:
                return True
        return False

    # Handle possible file move events by comparing file hashes
    def handle_possible_move(self, file_path, file_hash):
        current_time = datetime.now()
        for deleted_file, (hash_value, delete_time) in list(self.recently_deleted_files.items()):
            # Check if the hash matches and the deletion was recent (within 10 seconds)
            if hash_value == file_hash and (current_time - delete_time) < timedelta(seconds=10):
                # Log the move event with source and destination paths
                self.log_activity("file_moved", f"from {deleted_file} to {file_path}")
                # Remove the deleted file entry from the recently deleted files dictionary
                del self.recently_deleted_files[deleted_file]
                break

    # Calculate the MD5 hash of a file for tracking purposes
    def get_file_hash(self, file_path):
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                buf = f.read()
                hasher.update(buf)
            return hasher.hexdigest()
        except:
            return None

    # Check if the path is a system path to exclude it from monitoring
    def is_system_path(self, path):
        for system_dir in self.system_dirs:
            if path.startswith(system_dir):
                return True
        return False

    # Monitor open files and log activities related to opening and closing files
    def monitor_open_files(self):
        current_open_files = set()
        for proc in psutil.process_iter(['pid', 'name', 'username', 'open_files']):
            if proc.info['username'] == self.user and not self.is_background_service(proc):
                try:
                    open_files = proc.open_files()
                    for file in open_files:
                        file_path = file.path
                        if not self.is_system_path(file_path):
                            current_open_files.add(file_path)
                            if file_path not in self.open_files:
                                self.log_activity("file_opened", file_path)
                                self.recently_opened_files[file_path] = datetime.now()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

        # Determine which files have been closed since the last check
        closed_files = self.open_files - current_open_files
        for file_path in closed_files:
            self.log_activity("file_closed", file_path)

        # Update the set of open files
        self.open_files = current_open_files

    # Check if the process is a background service to exclude it from monitoring
    def is_background_service(self, proc):
        try:
            if proc.username() in ['SYSTEM', 'LOCAL SERVICE', 'NETWORK SERVICE']:
                return True
            parent = psutil.Process(proc.info['ppid'])
            if parent.name() in ['services.exe', 'svchost.exe']:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return True
        return False

# Main function to start monitoring
def main():
    # Get the current user's login name and device name
    user = os.getlogin()
    device = os.getenv('COMPUTERNAME')

    # Database configuration dictionary
    db_config = {
        'user': 'root',          # Database user
        'password': 'password',  # Database user's password
        'host': 'localhost',     # Database host
        'database': 'user_activity_monitor'  # Database name
    }

    # Set the directory to watch (root directory based on OS)
    directory_to_watch = "C:\\" if os.name == 'nt' else "/"

    # Initialize the event handler with the database configuration, user, and device
    event_handler = MyHandler(db_config, user, device)
    observer = Observer()

    # Schedule the observer to monitor the specified directory recursively
    observer.schedule(event_handler, directory_to_watch, recursive=True)

    # Start the observer
    observer.start()

    try:
        while True:
            # Monitor open files and log activities
            event_handler.monitor_open_files()
            time.sleep(10)  # Sleep for 10 seconds between checks
    except KeyboardInterrupt:
        # Stop the observer if the script is interrupted
        observer.stop()
    # Wait for the observer to finish
    observer.join()

# Main block to run the script
if __name__ == "__main__":
    main()
