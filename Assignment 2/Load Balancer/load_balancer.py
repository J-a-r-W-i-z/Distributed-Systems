from flask import Flask, request, jsonify
import mysql.connector
import os
import subprocess
import random

app = Flask(__name__)

def get_connection():
    try:
        # Connection parameters
        connection = mysql.connector.connect(host='localhost',
                                             database='your_database_name',
                                             user='your_username',
                                             password='your_password')
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Connected to MySQL Server version {db_info}")
            cursor = connection.cursor()
            return connection, cursor
        
    except Exception as e:
        print(f"Error: {e}")

def close_connection(connection, cursor):
    try:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")
    except Exception as e:
        print(f"Error: {e}")


@app.route('/init', methods=['POST'])
def init():
    pass # TODO: Implement this method
   
@app.route('/status', methods=['GET'])
def status():
    pass # TODO: Implement this method

@app.route('/add', methods=['POST'])
def add():
    pass # TODO: Implement this method

@app.route('/rm', methods=['DELETE'])
def rm():
    pass # TODO: Implement this method

@app.route('/read', methods=['POST'])
def read():
    pass # TODO: Implement this method

@app.route('/write', methods=['POST'])
def write():
    pass # TODO: Implement this method

@app.route('/update', methods=['PUT'])
def update():
    pass # TODO: Implement this method

@app.route('/del', methods=['DELETE'])
def delete():
    pass # TODO: Implement this method

def spawn_server(self, id, name, hostname, port):
        command = f"sudo docker run --name {name} --network assignment2_myNetwork --network-alias {name}  --hostname {hostname} -e SERVER_ID={id} -p {port}:5000 web-server"
        subprocess.Popen(command, shell=True)

def remove_server(self, container_name):
    os.system(f"sudo docker stop {container_name} && sudo docker rm {container_name}")

if __name__ == '__main__':
    
    app.run(debug=True, port=5000, threaded=True)
