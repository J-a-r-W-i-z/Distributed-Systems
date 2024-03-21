import bisect
from collections import deque
from flask import Flask, request, jsonify, Response
import mysql.connector
import os
import subprocess
import random
import copy
import requests
from time import sleep
import threading


import requests

app = Flask(__name__)
sql_connection_pool = None
NUM_SLOTS =512
MAX_RETRY = 100
LIVENESS_SLEEP_TIME = 5
NUM_REPLICA = 3
server_id_to_hostname = dict()
MAX_TIMEOUT = 10
server_id_to_shard = dict()
shard_data = []
read_result = []
SCHEMA = None
N = 0

# Consistent Hashing Data Structures
shard_to_server = {}
fast_server_assignment_map = {}

# Locks used in the code

sih_lock = threading.Lock()
sis_lock = threading.Lock()
mapT_lock = threading.Lock()
shardT_lock = threading.Lock()
n_lock = threading.Lock()
ss_lock,fsa_lock = threading.Lock(),threading.Lock()
shard_data_lock = threading.Lock()
write_lock_list = {}
read_count_lock_list = {}

read_count = {}


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
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS ShardT(Stud_id_low INT, Shard_id INT, Shard_size INT, Valid_idx INT)")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS MapT(Shard_id INT, Server_id INT)")
    # Bring information from ShardT and MapT tables to RAM for faster access

    cursor.close()
    connection.close()


@app.route('/')
def index():
    data = "Hello, World!"
    return jsonify(data)

@app.route('/init', methods=['POST'])
def init():
    global SCHEMA
    global shard_data
    global server_id_to_shard
    global N
    global shard_to_server
    global fast_server_assignment_map

    payload = request.json

    if 'N' not in payload or 'shards' not in payload or 'schema' not in payload :
        return jsonify({
            "message": "Payload must contain 'shards' and 'schema' keys",
            "status": "error"
        }), 400

    schema, shards, total_server = payload['schema'], payload['shards'], payload['N']
    N = total_server
    servers = {}
    if 'servers' not in payload:
        server_ids = []
        # generate server ids
        for _ in range(total_server):
            temp = random.randint(100000, 999999)
            while temp in server_ids:
                temp = random.randint(100000, 999999)
            server_ids.append(temp)

        num_shards = len(shards)
        server_picker_list = [[i for i in range(total_server)]]*num_shards

        for i in range(NUM_REPLICA):
            for j in range(num_shards):
                pos = random.choice(server_picker_list[j])
                server_id = server_ids[pos]
                if server_id not in servers:
                    servers[server_id] = []
                servers[server_id].append(shards[j]['Shard_id'])
                server_picker_list[j].remove(pos)

    else:
        servers = payload['servers']
        # make sure all server id and shard id's are integer
        temp_servers = {}

        for ss in servers.keys():
            temp_servers[convert_to_server_id(ss)] = [int(sh) for sh in servers[ss]]

        servers = temp_servers

        temp_shards = []
        for shard in shards:
            shard['Shard_id'] = int(shard['Shard_id'])
            temp_shards.append(shard)
        shards = temp_shards

            


    SCHEMA = schema
    with shard_data_lock:
        shard_data = shards
    with sis_lock:
        server_id_to_shard = servers
        print(f"Schema: {schema}, Shards: {shards}, Servers: {servers}")

    # make request to each server to create the database
    unsuccesful_servers = initialize_servers(servers)

    #initialize the shard_to_server and fast_server_assignment_map (Consistent Hashing Data Structures)
    with shard_data_lock:
        for shard in shard_data:
            shard_id = shard['Shard_id']
            shard_to_server[shard_id] = [None]*NUM_SLOTS
            fast_server_assignment_map [shard_id] = deque()
            write_lock_list[shard_id] = threading.Lock()
            read_count_lock_list[shard_id] = threading.Lock()
            read_count[shard_id] = 0




    # put the servers into consistent hashing data structure of each shard
    insert_data_into_chds(servers, unsuccesful_servers)

    # insert Data into ShardT Table (Stud id low: Number, Shard id: Number, Shard size:Number, valid idx:Number)
    insert_data_into_shard_table(shards)

    if len(unsuccesful_servers) > 0:
        N -= len(unsuccesful_servers)
        return jsonify({"message": "Couldn't spawn all servers successfully", "status": "error", "unsuccesful_servers": unsuccesful_servers}), 207

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
    with shard_data_lock:
     response['shards'] = shard_data
    with sis_lock:
        response['servers'] = server_id_to_shard

    return jsonify(response), 200


@app.route('/add', methods=['POST'])
def add():
    global N
    global shard_data

    payload = request.json

    if 'n' not in payload or 'new_shards' not in payload or 'servers' not in payload:
        return jsonify({
            "message": "Payload must contain 'n','new_shards' and 'server' keys",
            "status": "error"
        }), 400

    n, new_shards, servers = payload['schema'], payload['shards'], payload['servers']

    if n>len(servers):
        return jsonify({
            "message": "<Error> Number of new servers (n) is greater than newly added instances",
            "status": "failure"
        }), 400

    if n<len(servers):
        return jsonify({
            "message": "<Error> Number of new servers (n) is less than newly added instances",
            "status": "failure"
        }), 400
    with shard_data_lock:
        shard_data.extend(new_shards)
    # make sure all server id and shard id's are integer (Potential Bug: In copying the data structure)
    temp_servers = {}

    for ss in servers.keys():
        temp_servers[convert_to_server_id(ss)] = [int (sh) for sh in servers[ss]]

    servers = temp_servers

    temp_shards = []
    for shard in new_shards:
        shard['Shard_id'] = int(new_shards['Shard_id'])
        temp_shards.append(shard)
    new_shards = temp_shards


    # make request to each server to create the database
    unsuccesful_servers = initialize_servers(servers)

    #initialize the shard_to_server and fast_server_assignment_map (Consistent Hashing Data Structures)

    for shard in new_shards:
        shard_id = shard['Shard_id']
        shard_to_server[shard_id] = [None]*NUM_SLOTS
        fast_server_assignment_map [shard_id] = deque()
        write_lock_list[shard_id] = threading.Lock()
        read_count_lock_list[shard_id] = threading.Lock()
        read_count[shard_id] = 0

    # put the servers into consistent hashing data structure of each shard
    insert_data_into_chds(servers, unsuccesful_servers)

    # insert Data into ShardT Table (Stud id low: Number, Shard id: Number, Shard size:Number, valid idx:Number)
    insert_data_into_shard_table(new_shards)

    if len(unsuccesful_servers) > 0:
        N-=len(unsuccesful_servers)
        return jsonify({"message": "Couldn't spawn all servers successfully", "status": "error", "unsuccesful_servers": unsuccesful_servers}), 207

    N += n
    return jsonify({"N": N, "message": generate_response_string(list(servers.keys())), "status": "successful"}), 200


@app.route('/rm', methods=['DELETE'])
def rm():
    global N
    global shard_data
    payload = request.json

    if 'n' not in payload or 'servers' not in payload:
        return jsonify({
            "message": "Payload must contain 'n' and 'servers' keys",
            "status": "error"
        }), 400

    n, servers_to_remove = payload['n'], payload['servers']
    if n>N:
        return jsonify({
            "message": "<Error> Number of servers to remove (n) is greater than total instances",
            "status": "failure"
        }), 400

    if n<len(servers_to_remove):
        return jsonify({
            "message": "<Error> Number of servers to remove (n) is less than total instances",
            "status": "failure"
        }), 400

    temp_servers = []
    for ss in servers_to_remove:
        temp_servers.append(convert_to_server_id(ss))
    servers_to_remove = temp_servers



    if n>len(servers_to_remove):
        # randomly choose total N servers to remove
        with sih_lock:
            server_ids = list(server_id_to_hostname.keys())
        for ser in servers_to_remove:
            server_ids.remove(ser)
        while len(server_ids) !=n:
            random_servers = random.choice(server_ids)
            servers_to_remove.append(random_servers)
            server_ids.remove(random_servers)

    for server_id in servers_to_remove:
        remove_server(f"server{server_id}")
        remove_data_of_server(server_id)


    N-=n
    return jsonify({"N":N,"servers":[f"Server{ss}" for ss in servers_to_remove], "status": "successful"}), 200

@app.route('/read', methods=['POST'])
def read():
    global read_result

    payload = request.json
    if 'Stud_id' not in payload:
        return jsonify({
            "message": "Payload must contain 'Stud_id' key",
            "status": "error"
        }), 400
    stud_id = payload['Stud_id']

    low = stud_id['low']
    high = stud_id['high']
    # Get all shards in range
    shards = get_shards_in_range(low, high)
    num_thread = len(shards)
    threads = []
    read_result = []
    for i in range(num_thread):
        threads.append(threading.Thread(target=read_thread_runner, args=(shards[i],low, high)))
        threads[i].start()
    for i in range(num_thread):
        threads[i].join()


@app.route('/write', methods=['POST'])
def write():
    payload = request.json
    data = payload['data']
    # For Each entry:
    for entry in data:
        # Get shard_id from stud_id
        shard_id = get_shard_id_from_stud_id(entry['Stud_id'])
        with write_lock_list[shard_id]:
            # Get all servers where shard is present
            server_ids = get_servers_for_shards(shard_id)
            # Write entry in all replicas
            for server_id in server_ids:
                with sih_lock:
                    hostname = server_id_to_hostname[server_id]
                # Get valid_idx from ShardT table
                connection = sql_connection_pool.get_connection()

                cursor = connection.cursor()
                with shardT_lock:
                    cursor.execute(f'SELECT Valid_idx FROM ShardT WHERE Shard_id={shard_id}')
                valid_idx = cursor.fetchone()[0]
                cursor.close()
                connection.close()
                try:
                    response = requests.post(f"http://{hostname}:5000/write", json={"shard": shard_id, "curr_idx": valid_idx, "data": [entry]})
                    if response.status_code == 200:
                        print(f"Data successfully written to server {server_id}")
                    else:
                        print(f"Error occured while writing data to server {server_id}")
                except requests.exceptions.RequestException as e:
                    print(f"Exception occured while writing data to server {server_id}: {e}")
                    continue
                # Update vaild_idx in ShardT table
                connection = sql_connection_pool.get_connection()
                cursor = connection.cursor()
                with shardT_lock:
                    cursor.execute(f'UPDATE ShardT SET Valid_idx = Valid_idx + 1 WHERE Shard_id={shard_id}')
                cursor.close()
                connection.close()

    return jsonify({"message": f"{len(data)} Data entries added", "status": "success"}), 200


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
    payload = request.json
    data = payload['data']
    # Get shard_id from stud_id
    shard_id = get_shard_id_from_stud_id(data['Stud_id'])
    with write_lock_list[shard_id]:
        # Get all servers where shard is present
        server_ids = get_servers_for_shards(shard_id)
        # Write entry in all replicas
        for server_id in server_ids:
            with sih_lock:
                hostname = server_id_to_hostname[server_id]
            try:
                # Send put request to server to update the data
                response = requests.put(f"http://{hostname}:5000/update", json={"shard": shard_id, "Stud_id": payload['Stud_id'], "data": data})
                if response.status_code == 200:
                    print(f"Data successfully written to server {server_id}")
                else:
                    print(f"Error occured while writing data to server {server_id}")
            except requests.exceptions.RequestException as e:
                print(f"Exception occured while writing data to server {server_id}: {e}")
                continue
    return jsonify({"message": f"Data entry for Stud_id:{payload['Stud_id']} updated", "status": "success"}), 200


@app.route('/del', methods=['DELETE'])
def delete():
    payload = request.json
    # Get shard_id from stud_id
    shard_id = get_shard_id_from_stud_id(payload['Stud_id'])
    with write_lock_list[shard_id]:
        # Get all servers where shard is present
        server_ids = get_servers_for_shards(shard_id)
        # Write entry in all replicas
        for server_id in server_ids:
            with sih_lock:
                hostname = server_id_to_hostname[server_id]
            try:
                # Send del request to server to delete the data
                response = requests.delete(f"http://{hostname}:5000/del", json={"shard": shard_id, "Stud_id": payload['Stud_id']})
                if response.status_code == 200:
                    print(f"Data successfully written to server {server_id}")
                else:
                    print(f"Error occured while writing data to server {server_id}")
            except requests.exceptions.RequestException as e:
                print(f"Exception occured while writing data to server {server_id}: {e}")
                continue
    return jsonify({"message": f"Data entry with Stud_id:{payload['Stud_id']} removed", "status": "success"}), 200



# Utility Functions

def read_thread_runner(shard_id,low, high):
    global read_result
    # Get all servers where shard is present
    request_id = random.randint(100000, 999999)
    server_id = get_server_assignment(shard_id,request_id)
    # Read data from all replicas
    with sih_lock:
        hostname = server_id_to_hostname[server_id]
    try:
        # Send get request to server to read the data
        response = requests.get(f"http://{hostname}:5000/read", json={"shard": shard_id,"Stud_id": {"low": low, "high": high}})
        if response.status_code == 200:
            print(f"Data successfully read from server {server_id}")
            read_result.extend(response.json()["data"])
        else:
            print(f"Error occured while reading data from server {server_id}")
    except requests.exceptions.RequestException as e:
        print(f"Exception occured while reading data from server {server_id}: {e}")


def get_request_hash(request_id):
    # Get hash of request_id
    temp = (request_id*37)*(request_id+71)+ 47 + 293
    return temp % 512
def get_server_assignment(shard_id,request_id):
    hash = get_request_hash(request_id)
    # get upper bound of hash in the fast access list
    pos = bisect.bisect_left(fast_server_assignment_map[shard_id],hash)
    if pos == len(fast_server_assignment_map[shard_id]):
        pos = 0
    return shard_to_server[shard_id][fast_server_assignment_map[shard_id][pos]]



def generate_response_string(servers):
    result = ""
    for i, num in enumerate(servers):
        result += f"Server: {num}"
        if i < len(servers) - 1:
            result += ", "
        if i == len(servers) - 2:
            result += "and "

    return result


def initialize_servers(servers):
    global server_id_to_hostname

    unsuccesful_servers = {}
    for server_id in servers.keys():
        hostname = f"server{server_id}"
        print(f"Making request to server {server_id} with hostname {hostname} to create database {SCHEMA}")
        spawn_server(server_id, hostname, hostname)
        if spawned_successfully(hostname, servers[server_id]):
            print("Server spawned successfully")
            add_data_of_server(server_id, hostname, servers[server_id])
        else:
            print(f"Couldn't spawn server {server_id} with hostname {hostname} ")
            unsuccesful_servers[server_id] = servers[server_id]
    
    return unsuccesful_servers

def insert_data_into_chds(servers, unsuccesful_servers=[]):
    global shard_to_server
    global fast_server_assignment_map

    for server_id in servers.keys():
        if server_id not in unsuccesful_servers:
            for shard_id in servers[server_id]:
                pos = get_server_slot(server_id, shard_id)
                shard_to_server[shard_id][pos] = server_id
                bisect.insort_left(fast_server_assignment_map[shard_id],pos)



def insert_data_into_shard_table(data):
    # insert Data into ShardT Table (Stud id low: Number, Shard id: Number, Shard size:Number, valid idx:Number)
    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    for shard in data:
        Stud_id_low, shard_size, shard_id = shard['Stud_id_low'], shard['Shard_size'], shard['Shard_id']
        cursor.execute(f"INSERT INTO ShardT VALUES ({Stud_id_low}, {shard_id}, {shard_size}, 0)")
    cursor.close()
    connection.close()

def get_server_slot(server_id, shard_id):
    global shard_to_server
    temp  = (server_id*37)*(server_id+71)+ shard_id*47 + 293
    slot = temp % NUM_SLOTS
    while shard_to_server[shard_id][slot] is not None:
        slot = (slot+1)%NUM_SLOTS
    return slot


def convert_to_server_id(server_name):
    return int(server_name[6:])

def get_shard_id_from_stud_id(stud_id):
    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    with shardT_lock:
        cursor.execute(f"SELECT Shard_id FROM ShardT WHERE Stud_id_low <= {stud_id} ORDER BY Stud_id_low DESC LIMIT 1")
    shard_id = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    return shard_id

def get_server_id():
    number = random.randint(100000, 999999)
    with sih_lock:
        while number in server_id_to_hostname:
            number = random.randint(100000, 999999)
    return number

def spawn_server(id, name, hostname):
        command = f"sudo docker run --network assignment2_myNetwork --name {name} --hostname {hostname} -e SERVER_ID={id} web-server"
        subprocess.Popen(command, shell=True)

def spawned_successfully(hostname, shard_ids):
    tries = 0
    while True:
        if tries > MAX_RETRY:
            print("Max retry limit reached.\n Couldn't connect to Server\n ")
            return False
        try:
            response = requests.get(f"http://{hostname}:5000/heartbeat")
            if response.status_code == 200:
                # Call config method on server
                response = requests.post(f"http://{hostname}:5000/config", json={"schema": SCHEMA, "shards": shard_ids})
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
    # remove data from server_id_to_hostname and server_id_to_shard
    with sih_lock:
        del server_id_to_hostname[server_id]
    with sis_lock,ss_lock,fsa_lock:
        del server_id_to_shard[server_id]

        # remove data from consistent hashing data structures
        for shard_id in server_id_to_shard[server_id]:
            for i in range(NUM_SLOTS):
                if shard_to_server[shard_id][i] == server_id:
                    shard_to_server[shard_id][i] = None
                    fast_server_assignment_map[shard_id].remove(i)

    # remove from the MapT table

    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    with mapT_lock:
        cursor.execute(f"DELETE FROM MapT WHERE Server_id={server_id}")
    cursor.close()
    connection.close()

def get_server_for_shard(shard_id):
    # TODO : Can update for faster access from RAM
    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    with mapT_lock:
        cursor.execute(f"SELECT Server_id FROM MapT WHERE Shard_id={shard_id}")
    server_id = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    return server_id

def get_servers_for_shards(shard_id):
    # TODO : Can update for faster access from RAM
    connection = sql_connection_pool.get_connection()
    cursor = connection.cursor()
    with mapT_lock:
        cursor.execute(f"SELECT Server_id FROM MapT WHERE Shard_id={shard_id}")
    server_ids = cursor.fetchall()
    cursor.close()
    connection.close()
    return server_ids

def get_shards_in_range(lo, hi):
    # Declare a set
    shards = set()
    id = lo
    while id<=hi:
        shard_id = get_shard_id_from_stud_id(id)
        shards.add(shard_id)
        id+=shard_data[0]['Shard_size']
    shard_id = get_shard_id_from_stud_id(hi)
    shards.add(shard_id)
    # Convert set to list
    return list(shards)

def liveness_checker():
    while True:
        sleep(LIVENESS_SLEEP_TIME)
        with sih_lock:
            sih_copy = copy.deepcopy(server_id_to_hostname)

        shard_ids_for_new_servers = []      # List of lists
        for server_id, hostname in sih_copy.items():
            try:
                response = requests.get(f"http://{hostname}:5000/heartbeat")
                if response.status_code != 200:
                    print(f"Server {server_id} with hostname {hostname} is dead. Removing it from Load Balancer...")
                    try:
                        with sis_lock:
                            if server_id not in server_id_to_shard:
                                continue
                            shard_ids_for_new_servers.append(server_id_to_shard[server_id])
                        remove_server(f"server{server_id}")
                        remove_data_of_server(server_id)
                    except Exception as e:
                        print(f"Server already deleted")
            except requests.exceptions.RequestException as e:
                print(f"Error occured while making request to server {server_id} to check if alive: {e}")
                print(f"Removing it from Load Balancer...")
                try:
                    with sis_lock:
                        if server_id not in server_id_to_shard:
                            continue
                        shard_ids_for_new_servers.append(server_id_to_shard[server_id])
                    remove_server(f"server{server_id}")
                    remove_data_of_server(server_id)
                except Exception as e:
                    print(f"Server already deleted")

        # Spawn new servers for shards of dead servers
        for i in range(len(shard_ids_for_new_servers)):
            server_id = get_server_id()
            hostname = f"server{server_id}"
            spawn_server(server_id, hostname, hostname)
            if spawned_successfully(hostname, shard_ids_for_new_servers[i]):
                add_data_of_server(server_id, hostname, shard_ids_for_new_servers[i])
                insert_data_into_chds({server_id: shard_ids_for_new_servers[i]})
            else:
                print(f"Couldn't spawn server {server_id} with hostname {hostname} successfully")

            for shard_id in shard_ids_for_new_servers[i]:
                source_server_id = get_server_for_shard(shard_id)
                # Get data from source server using copy endpoint
                with sih_lock:
                    source_hostname = server_id_to_hostname[source_server_id]
                try:
                    response = requests.get(f"http://{source_hostname}:5000/copy", json={"shards": [shard_id]})
                    # Get response data
                    data = response.json()
                    list_of_entires = data[shard_id]
                    # Get valid_idx from ShardT table
                    connection = sql_connection_pool.get_connection()
                    cursor = connection.cursor()
                    with shardT_lock:
                        cursor.execute(f"SELECT Valid_idx FROM ShardT WHERE Shard_id={shard_id}")
                    valid_idx = cursor.fetchone()[0]
                    cursor.close()
                    connection.close()
                    # Insert data into new server using write endpoint
                    response = requests.post(f"http://{hostname}:5000/write", json={"shard": shard_id, "curr_idx": valid_idx, "data": list_of_entires})
                    if response.status_code == 200:
                        print(f"Data successfully copied from server {source_server_id} to server {server_id}")
                    else:
                        print(f"Error occured while transfering data")
                except requests.exceptions.RequestException as e:
                    print(f"Error occured while transfering data")
                    continue


def remove_server(container_name):
    os.system(f"sudo docker stop {container_name} && sudo docker rm {container_name}")

if __name__ == '__main__':
    print("Running load balancer...")
    connect_to_sql_server()
    initialize_metadata_tables()
    liveness_checker_thread = threading.Thread(target=liveness_checker)
    liveness_checker_thread.start()
    app.run(debug=False, port=5000, host="0.0.0.0", threaded=True)
