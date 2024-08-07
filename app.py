from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app)

db_config = {
    'user': 'root',
    'password': 'password',
    'host': 'localhost',
    'database': 'user_activity_monitor'
}

def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

@app.route('/users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT DISTINCT user FROM user_activity"
        cursor.execute(query)
        
        users = cursor.fetchall()
        print("Fetched users:", users)  # Debugging statement
        cursor.close()
        conn.close()
        
        return jsonify(users)
    except Exception as e:
        print("Error:", str(e))  # Debugging statement
        return jsonify({"error": str(e)}), 500

@app.route('/activities', methods=['GET'])
def get_activities():
    try:
        user = request.args.get('user')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM user_activity WHERE user=%s ORDER BY timestamp DESC"
        cursor.execute(query, (user,))
        
        activities = cursor.fetchall()
        print("Fetched activities for user:", user, activities)  # Debugging statement
        cursor.close()
        conn.close()
        
        return jsonify(activities)
    except Exception as e:
        print("Error:", str(e))  # Debugging statement
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
