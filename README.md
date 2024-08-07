Tracking User Activity Software
Description

This software is designed to monitor and log user activity on a Windows system. It tracks file operations (creation, modification, deletion, renaming) while excluding system directories and background services. The logged activities are stored in a MySQL database and can be accessed via a web interface.
What Logs Are Being Stored

    File Operations:
        file_created: When a file is created.
        file_modified: When a file is modified.
        file_deleted: When a file is deleted.
        file_renamed: When a file is renamed.

    Each log entry includes:
        user: The username of the logged-in user.
        device: The name of the device where the activity was detected.
        activity_type: The type of activity.
        details: Detailed information about the activity.
        timestamp: The date and time when the activity was detected.

Execute MySQL Query to create a database.

Run activity_monitor.py to Start Monitoring:

    Ensure Python and the required libraries (watchdog, psutil, mysql-connector-python) are installed.
    
    Update the database configuration in activity_monitor.py:
    db_config = {
    'user': 'your_user_name',
    'password': 'your_password',
    'host': 'localhost',
    'database': 'database_name'
}

Run the script to start monitoring:
python activity_monitor.py

Run app.py to Start the Server:

Ensure Flask and Flask-CORS are installed:
pip install flask flask-cors

Start the server to access logs via the website:
python app.py

Accessing Logs via Website

Open your web browser and navigate to:

http://127.0.0.1:5000

View Logs:

Select the user to view their activity logs.


