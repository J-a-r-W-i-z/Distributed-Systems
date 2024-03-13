from flask import Flask, jsonify
import mysql.connector

app = Flask(__name__)

# MySQL configuration
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'password',
    'database': 'mydb'
}

# Connect to MySQL

@app.route('/')
def index():
    data = "Hello, World!"
    return jsonify(data)

@app.route('/test')
def gett():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute("SELECT user FROM mysql.user;")
    cursor.reset()
    cursor.close()
    return jsonify("Success")

if __name__ == '__main__':
    print("Started flask server")
    app.run(debug=True, host='0.0.0.0')
