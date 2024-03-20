from flask import Flask, request, jsonify, Response
import mysql.connector
import os
import subprocess
import random
import requests
from time import sleep
import threading


import requests

app = Flask(__name__)
sql_connection_pool = None
MAX_RETRY = 100
LIVENESS_SLEEP_TIME = 5
server_id_to_hostname = dict()
MAX_TIMEOUT = 10
server_id_to_shard = dict()
shard_data = []
SCHEMA = None
N = 0

sih_lock = threading.Lock()
sis_lock = threading.Lock()
mapT_lock = threading.Lock()
shardT_lock = threading.Lock()
n_lock = threading.Lock()

def connect_to_sql_server(max_pool_size=30, host='localhost', user='root', password='password', database='mydb'):
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



def initialize_metadata_tables():
    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS ShardT(Stud_id_low INT, Shard_id INT, Shard_size INT, Valid_idx INT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS MapT(Shard_id INT, Server_id INT)")
    # Bring information from ShardT and MapT tables to RAM for faster access

    cursor.close()
    connection.close()

@app.route('/')
def index():
    data = "Hello, World!"
    return jsonify(data)
@app.route('/<user_path>', methods=['GET'])
def index(user_path):
    response = requests.get(f"http://server1:5000/{user_path}")
    filtered_headers = {key: value for key, value in response.headers.items()
                        if key.lower() in ['content-type', 'content-length', 'connection', 'date']}
    
    return Response(response.content, status=response.status_code, headers=filtered_headers)

@app.route('/test', methods=['GET'])
def gett():
    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT user FROM mysql.user;")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    cursor.close()
    connection.close()
    return jsonify("Success")

@app.route('/init', methods=['POST'])
def init():
    global SCHEMA
    global shard_data
    global server_id_to_shard
    payload = request.json

    if 'shards' not in payload or 'schema' not in payload or 'servers' not in payload:
        return jsonify({
            "message": "Payload must contain 'shards' and 'schema' keys",
            "status": "error"
        }), 400

    schema, shards,servers = payload['schema'], payload['shards'],payload['servers']
    SCHEMA = schema
    shard_data = shards 
    server_id_to_shard = servers
    print(f"Schema: {schema}, Shards: {shards}, Servers: {servers}")
    # make request to each server to create the database
    unsucessful_list=[]
    for server_id in servers.keys():
        hostname = server_id_to_hostname[server_id] 
        print(f"Making request to server {server_id} with hostname {hostname} to create database {schema}")
        try:
            response = requests.post(f"http://{hostname}/config", json={"schema": schema,"shards": servers[server_id]},timeout=MAX_TIMEOUT)
            if response.status_code != 200:
                print(f"Error occured while making request to server {server_id} with hostname {hostname} to create database {schema}: {response.json()}")
                return jsonify({
                    "message": f"Couldn't configure server {server_id} with hostname {hostname} to create database",
                    "status": "error"
                }), 500
            
        except requests.exceptions.RequestException as e:
            print(f"Error occured while making request to server {server_id} with hostname {hostname} to create database {schema}: {e}")
            unsucessful_list.append(server_id)
    
    if len(unsucessful_list)>0:
        return jsonify({"message": "Failed to configure servers some server to create database", "status": "error","servers":unsucessful_list}), 206


         

    # insert Data into ShardT Table (Stud id low: Number, Shard id: Number, Shard size:Number, valid idx:Number)
    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    for shard in shards:
        Stud_id_low, shard_size, shard_id = shard['Stud_id_low'], shard['Shard_size'], shard['Shard_id']
        cursor.execute(f"INSERT INTO ShardT VALUES ({Stud_id_low}, {shard_id}, {shard_size}, 0)")
    # insert Data into MapT table (Shard id: Number, Server id: Number)
    for server_id in servers.keys():
        corr_shards = servers[server_id]
        for shard_id in corr_shards:
            cursor.execute(f"INSERT INTO MapT VALUES ({shard_id}, {server_id})")
    
    cursor.close()
    connection.close()

    return jsonify({"message": "Successfully configured all servers to create database", "status": "success"}), 200
   
@app.route('/status', methods=['GET'])
def status():
    response = dict()
    # lock
    with sih_lock:
        total_servers = len(server_id_to_hostname)
    # unlock

    response['N'] = total_servers 
    response['schema'] = SCHEMA
    response['shards'] = shard_data
    response['servers'] = server_id_to_shard

    return jsonify(response), 200


@app.route('/add', methods=['POST'])
def add():
    payload = request.json

    if 'n' not in payload or 'new_shards' not in payload or 'servers' not in payload:
        return jsonify({
            "message": "Payload must contain 'n','new_shards' and 'server' keys",
            "status": "error"
        }), 400

    schema, shards,servers = payload['schema'], payload['shards'],payload['servers']

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
    - acquire read_count_lock
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

def get_server_id():
    number = random.randint(100000, 999999)
    with sih_lock:
        while number in server_id_to_hostname:
            number = random.randint(100000, 999999)
    return number

def spawn_server(id, name, hostname):
        command = f"sudo docker run --network assignment2_myNetwork --name {name} --hostname {hostname} -e SERVER_ID={id} web-server"
        subprocess.Popen(command, shell=True)

def spawned_successfully(hostname):
    tries = 0
    while True:
        if tries > MAX_RETRY:
            print("Max retry limit reached.\n Couldn't connect to Server\n ")
            return False
        try:
            response = requests.get(f"http://{hostname}:5000/hearbeat")
            if response.status_code == 200:
                return True
            else:
                tries += 1
                sleep(3)
        except requests.exceptions.RequestException as e:
            tries += 1
            print(f"Error occured while making request to server {hostname} to check if spawned: {e}")
            sleep(3)

def add_data_of_server(server_id, hostname, shard_ids):
    with sih_lock:
        server_id_to_hostname[server_id] = hostname
    with sis_lock:
        server_id_to_shard[server_id] = shard_ids

    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    with mapT_lock:
        for shard_id in shard_ids:
            cursor.execute(f"INSERT INTO MapT VALUES ({shard_id}, {server_id})")
    cursor.close()
    connection.close()

def remove_data_of_server(server_id):
    with sih_lock:
        del server_id_to_hostname[server_id]
    with sis_lock:
        del server_id_to_shard[server_id]

    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    with mapT_lock:
        cursor.execute(f"DELETE FROM MapT WHERE Server_id={server_id}")
    cursor.close()
    connection.close()

def liveness_checker():
    while True:
        sleep(LIVENESS_SLEEP_TIME)
        with sih_lock:
            sih_copy = server_id_to_hostname
        for server_id, hostname in sih_copy.items():
            try:
                response = requests.get(f"http://{hostname}:5000/hearbeat")
                if response.status_code != 200:
                    print(f"Server {server_id} with hostname {hostname} is dead. Removing it from Load Balancer...")
                    try:
                        remove_server(f"server{server_id}")
                        remove_data_of_server(server_id)
                    except Exception as e:
                        print(f"Server already deleted")
            except requests.exceptions.RequestException as e:
                print(f"Error occured while making request to server {server_id} to check if alive: {e}")
                print(f"Removing it from Load Balancer...")
                try:
                    remove_server(f"server{server_id}")
                    remove_data_of_server(server_id)
                except Exception as e:
                    print(f"Server already deleted")
        
        with n_lock, sih_lock:
            num_servers_to_be_spawned = N - len(server_id_to_hostname)
        
        for i in range(num_servers_to_be_spawned):
            server_id = get_server_id()
            hostname = f"server{server_id}"
            spawn_server(server_id, hostname)
            if spawned_successfully(hostname):
                add_data_of_server(server_id, hostname, [])
            else:
                print(f"Couldn't spawn server {server_id} with hostname {hostname}")


def remove_server(container_name):
    os.system(f"sudo docker stop {container_name} && sudo docker rm {container_name}")

if __name__ == '__main__':
    print("Running load balancer...")
    connect_to_sql_server()
    initialize_metadata_tables()
    print("Creating Servers...")
    for i in range(1,4):
        spawn_server(i, f"server{i}", f"server{i}", 5000+i)
        print(f"Server {i} created")
    liveness_checker_thread = threading.Thread(target=liveness_checker)
    liveness_checker_thread.start()
    app.run(debug=False, port=5000, host="0.0.0.0", threaded=True)
