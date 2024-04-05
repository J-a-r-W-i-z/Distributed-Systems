import bisect
from collections import deque
import queue
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

LIVENESS_SLEEP_TIME = 5
app = Flask(__name__)

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
                    if response.status_code !=200:
                        print(response.json())
                    # Get response data
                    data = response.json()
                    list_of_entires = data[str(shard_id)]
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