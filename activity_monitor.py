import os
import psutil
import mysql.connector
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timedelta
import time
import hashlib

class MyHandler(FileSystemEventHandler):
    def __init__(self, db_config, user, device):
        self.conn = mysql.connector.connect(**db_config)
        self.cursor = self.conn.cursor()
        self.user = user
        self.device = device
        self.system_dirs = [
            'C:\\Windows',
            'C:\\ProgramData',
            'C:\\Program Files',
            'C:\\Program Files (x86)',
            os.getenv('APPDATA'),
            os.getenv('LOCALAPPDATA')
        ]
        self.logged_events = set()
        self.open_files = set()
        self.recently_opened_files = {}
        self.recently_deleted_files = {}

    def log_activity(self, activity_type, details):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        event_key = (activity_type, details, timestamp)
        if event_key not in self.logged_events:
            query = "INSERT INTO user_activity (user, device, activity_type, details, timestamp) VALUES (%s, %s, %s, %s, %s)"
            values = (self.user, self.device, activity_type, details, timestamp)
            self.cursor.execute(query, values)
            self.conn.commit()
            self.logged_events.add(event_key)

    def on_modified(self, event):
        if not self.is_system_path(event.src_path) and not event.is_directory:
            if not self.was_recently_opened(event.src_path):
                self.log_activity("file_modified", event.src_path)

    def on_created(self, event):
        if not self.is_system_path(event.src_path):
            if event.is_directory:
                self.log_activity("folder_created", event.src_path)
            else:
                file_hash = self.get_file_hash(event.src_path)
                self.handle_possible_move(event.src_path, file_hash)
                self.log_activity("file_created", event.src_path)

    def on_deleted(self, event):
        if not self.is_system_path(event.src_path):
            if event.is_directory:
                self.log_activity("folder_deleted", event.src_path)
            else:
                file_hash = self.get_file_hash(event.src_path)
                self.recently_deleted_files[event.src_path] = (file_hash, datetime.now())
                self.log_activity("file_deleted", event.src_path)

    def on_moved(self, event):
        if not self.is_system_path(event.src_path):
            self.log_activity("file_moved", f"from {event.src_path} to {event.dest_path}")

    def was_recently_opened(self, file_path):
        if file_path in self.recently_opened_files:
            event_time = self.recently_opened_files[file_path]
            if (datetime.now() - event_time).seconds < 10:
                return True
        return False

    def handle_possible_move(self, file_path, file_hash):
        current_time = datetime.now()
        for deleted_file, (hash_value, delete_time) in list(self.recently_deleted_files.items()):
            if hash_value == file_hash and (current_time - delete_time) < timedelta(seconds=10):
                self.log_activity("file_moved", f"from {deleted_file} to {file_path}")
                del self.recently_deleted_files[deleted_file]
                break

    def get_file_hash(self, file_path):
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                buf = f.read()
                hasher.update(buf)
            return hasher.hexdigest()
        except:
            return None

    def is_system_path(self, path):
        for system_dir in self.system_dirs:
            if path.startswith(system_dir):
                return True
        return False

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

        closed_files = self.open_files - current_open_files
        for file_path in closed_files:
            self.log_activity("file_closed", file_path)

        self.open_files = current_open_files

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

def main():
    user = os.getlogin()
    device = os.getenv('COMPUTERNAME')

    db_config = {
        'user': 'root',
        'password': 'password',
        'host': 'localhost',
        'database': 'user_activity_monitor'
    }

    # Watch the entire filesystem
    directory_to_watch = "C:\\" if os.name == 'nt' else "/"

    event_handler = MyHandler(db_config, user, device)
    observer = Observer()

    observer.schedule(event_handler, directory_to_watch, recursive=True)

    observer.start()

    try:
        while True:
            event_handler.monitor_open_files()
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
