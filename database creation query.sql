-- Create the database
CREATE DATABASE user_activity_monitor;

-- Switch to the new database
USE user_activity_monitor;

-- Create the user_activity table
CREATE TABLE user_activity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user VARCHAR(255),
    device VARCHAR(255),
    activity_type VARCHAR(255),
    details TEXT,
    timestamp DATETIME
);

-- Create a user for accessing the database (optional, for better security)
CREATE USER 'activity_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON user_activity_monitor.* TO 'activity_user'@'localhost';
FLUSH PRIVILEGES;
