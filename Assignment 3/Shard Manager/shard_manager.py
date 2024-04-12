import bisect
from collections import deque
import queue
from flask import Flask, request, jsonify, Response
import os
import subprocess
import random
import copy
import requests
from time import sleep
import threading
import requests

PRIMARY_SERVERS = {}  # shard_id -> server_id

LIVENESS_SLEEP_TIME = 300
app = Flask(__name__)


@app.route('/primary_elect', methods=['POST'])
def primary_elect():
    shard_id = request.json["shard_id"]
    server_id_to_shard = requests.get(
        "http://lb:5000/get_server_id_to_shard").json()
    servers_to_hostname = requests.get(
        "http://lb:5000/get_server_to_hostname").json()
    servers = []
    for server_id, shard_ids in server_id_to_shard.items():
        if shard_id in shard_ids:
            servers.append(server_id)
    if len(servers) == 0:
        return Response(status=404)
    wal_length = []
    for server in servers:
        print("server:", servers_to_hostname[server])
        response = requests.post(
            f"http://{servers_to_hostname[server]}:5000/wal", json={"shard": shard_id})
        lines = response.text.split("\n")
        wal_length.append(len(lines))
    max_wal_length = max(wal_length)
    candidates = []
    for i in range(len(servers)):
        if wal_length[i] == max_wal_length:
            candidates.append(servers[i])
    primary_server = random.choice(candidates)
    secondary_servers = []
    for server in servers:
        if server != primary_server:
            secondary_servers.append(servers_to_hostname[server])
    try:
        PRIMARY_SERVERS[shard_id] = primary_server
        response = requests.post(f"http://{servers_to_hostname[primary_server]}:5000/make_primary", json={
                                 "shard": shard_id, "secondary": secondary_servers})
        if response.status_code != 200:
            raise Exception()
    except:
        print("Could not make selected server primary")
        return Response(status=500)
    return Response(status=200)


@app.route('/update_primary_if_required', methods=['POST'])
def update_primary_if_required():
    deleted_servers = request.json["deleted_servers"]
    for shard_id, server_id in PRIMARY_SERVERS.items():
        if server_id in deleted_servers:
            response = requests.post(
                "http://sm:5000/primary_elect", json={"shard_id": shard_id})
            print(response.status_code)


@app.route('/get_primary', methods=['GET'])
def get_primary():
    return jsonify(PRIMARY_SERVERS)


def liveness_checker():
    while True:
        sleep(LIVENESS_SLEEP_TIME)

        try:
            # Get the list of all the servers
            servers_to_hostname = requests.get(
                "http://lb:5000/get_server_to_hostname").json()
        except:
            continue

        shard_ids_for_new_servers = []      # List of lists
        for server_id, hostname in servers_to_hostname.items():
            response = requests.get(f"http://{hostname}:5000/heartbeat")
            if response.status_code != 200:
                # Get updated list of servers
                server_id_to_shard = requests.get(
                    "http://lb:5000/get_server_id_to_shard").json()
                if server_id not in server_id_to_shard:
                    continue
                shard_ids_for_new_servers.append(server_id_to_shard[server_id])
                requests.post("http://lb:5000/remove_metadata",
                              json={"server_id": server_id})
                requests.post("http://sm:5000/update_primary_if_required",
                              json={"deleted_servers": [server_id]})

        if len(shard_ids_for_new_servers) == 0:
            continue
        # Spawn new servers for shards of dead servers
        requests.post("http://lb:5000/spawn_servers",
                      json={"shard_ids_for_new_servers": shard_ids_for_new_servers})


if __name__ == '__main__':
    threading.Thread(target=liveness_checker).start()
    app.run(debug=False, port=5000, host="0.0.0.0", threaded=True)
