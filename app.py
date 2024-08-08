from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector

# Initialize a Flask application
app = Flask(__name__)
# Enable Cross-Origin Resource Sharing (CORS) for the app, allowing requests from different origins
CORS(app)

# Configuration dictionary for database connection
db_config = {
    'user': 'root',          # Database user
    'password': 'password',  # Database user's password
    'host': 'localhost',     # Database host
    'database': 'user_activity_monitor'  # Database name
}

# Function to establish a connection to the MySQL database
def get_db_connection():
    # Connect to the MySQL database using the provided configuration
    conn = mysql.connector.connect(**db_config)
    return conn

# Define a route to get a list of distinct users
@app.route('/users', methods=['GET'])
def get_users():
    try:
        # Establish a database connection
        conn = get_db_connection()
        # Create a cursor object with dictionary format for results
        cursor = conn.cursor(dictionary=True)
        
        # SQL query to select distinct users from the user_activity table
        query = "SELECT DISTINCT user FROM user_activity"
        cursor.execute(query)
        
        # Fetch all distinct users
        users = cursor.fetchall()
        print("Fetched users:", users)  # Debugging statement to print fetched users
        # Close the cursor and connection
        cursor.close()
        conn.close()
        
        # Return the list of users as JSON
        return jsonify(users)
    except Exception as e:
        # Print error message for debugging
        print("Error:", str(e))  # Debugging statement to print error
        # Return an error message as JSON with status code 500 (Internal Server Error)
        return jsonify({"error": str(e)}), 500

# Define a route to get the activities of a specific user
@app.route('/activities', methods=['GET'])
def get_activities():
    try:
        # Get the 'user' parameter from the request URL
        user = request.args.get('user')
        # Establish a database connection
        conn = get_db_connection()
        # Create a cursor object with dictionary format for results
        cursor = conn.cursor(dictionary=True)
        
        # SQL query to select all activities of the specified user, ordered by timestamp in descending order
        query = "SELECT * FROM user_activity WHERE user=%s ORDER BY timestamp DESC"
        # Execute the query with the user parameter
        cursor.execute(query, (user,))
        
        # Fetch all activities for the specified user
        activities = cursor.fetchall()
        print("Fetched activities for user:", user, activities)  # Debugging statement to print fetched activities
        # Close the cursor and connection
        cursor.close()
        conn.close()
        
        # Return the list of activities as JSON
        return jsonify(activities)
    except Exception as e:
        # Print error message for debugging
        print("Error:", str(e))  # Debugging statement to print error
        # Return an error message as JSON with status code 500 (Internal Server Error)
        return jsonify({"error": str(e)}), 500

# Main block to run the Flask application
if __name__ == '__main__':
    # Run the Flask app in debug mode
    app.run(debug=True)
