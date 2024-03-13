from flask import Flask, request, jsonify
import mysql.connector
import os
import subprocess
import random
from time import sleep

app = Flask(__name__)
sql_connection_pool = None
MAX_RETRY = 1000

def connect_to_sql_server(max_pool_size=5, host='localhost', user='root', password='password', database='mydb'):
    global sql_connection_pool
    flag = True
    tries = 0
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

@app.route('/')
def index():
    data = "Hello, World!"
    return jsonify(data)

@app.route('/test')
def gett():
    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    # cursor = sql_connection_pool.cursor()
    cursor.execute("SELECT user FROM mysql.user;")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    cursor.close()
    connection.close()
    return jsonify("Success")

@app.route('/init', methods=['POST'])
def init():
    payload = request.json

    if 'shards' not in payload or 'schema' not in payload or 'servers' not in payload:
        return jsonify({
            "message": "Payload must contain 'shards' and 'schema' keys",
            "status": "error"
        }), 400

    schema, shards,servers = payload['schema'], payload['shards'],payload['servers']
    print(f"Schema: {schema}, Shards: {shards}, Servers: {servers}")
    # insert Data into ShardT Table (Stud id low: Number, Shard id: Number, Shard size:Number, valid idx:Number)
    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    for shard in shards:
        Stud_id_low, shard_size, shard_id = shard['Stud_id_low'], shard['Shard_size'], shard['shard_id']
        cursor.execute(f"INSERT INTO ShardT VALUES ({Stud_id_low}, {shard_id}, {shard_size}, 0)")
    # insert Data into MapT table (Shard id: Number, Server id: Number)
    for server in servers:
        server_id, shard_id = server['server_id'], server['shard_id']
        cursor.execute(f"INSERT INTO MapT VALUES ({shard_id}, {server_id})")
    

   
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

def spawn_server(id, name, hostname, port):
        command = f"sudo docker run -p {port}:5000 --name {name} --network assignment2_myNetwork --network-alias {name}  --hostname {hostname} -e SERVER_ID={id} web-server"
        subprocess.Popen(command, shell=True)

def remove_server(container_name):
    os.system(f"sudo docker stop {container_name} && sudo docker rm {container_name}")

if __name__ == '__main__':
    print("Running load balancer...")
    connect_to_sql_server()
    print("Creating Servers...")
    for i in range(1,4):
        spawn_server(i, f"server{i}", f"server{i}", 5000+i)
        print(f"Server {i} created")
    app.run(debug=False, port=5000, host="0.0.0.0", threaded=True)
