from flask import Flask, request, jsonify
import mysql.connector
import os
import subprocess
import random
from time import sleep

app = Flask(__name__)
sql_connection_pool = None
MAX_RETRY = 1000

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

def connect_to_sql_server(max_pool_size=5, host='localhost', user='root', password='password', database='test'):
    global sql_connection_pool
    flag = True
    tries =0
    while True:
        if tries > MAX_RETRY:
            print("Max retry limit reached.\n Couldn't connect to MySql server\n Exiting...")
            exit(1)
        try:
            if flag:
                print("Creating MySQL connection pool...")
                flag = False
            else:
                print("Retrying to connect to mysql server...")
                sleep(3)
            if sql_connection_pool is None:
                sql_connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                    pool_name="my_pool",
                    pool_size=max_pool_size,
                    host=host,
                    user=user,
                    password=password,
                    database=database
                )
                return
        except Exception as e:
            tries += 1
            print(f"Error occursed while connecting to sql server: {e}")

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
     # TODO: Implement this method
    pass
'''
read and write locks
    - read lock: multiple clients can read at the same time
    - write lock: only one client can write at a time
 -- Reading task:
    - acquire read_count lock
    - increment read_count
    - if read_count == 1
        - acquire write lock
    - release read_count lock
    - read data
    - acquire read_count lock
    - decrement read_count
    - if read_count == 0
        - release write lock
    - release read_count lock
    
-- Writing task:
    - acquire write lock
    - write data
    - release write lock


'''



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
