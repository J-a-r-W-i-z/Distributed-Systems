import math
import os
import random
import requests
import sys
import time
import concurrent.futures

BASE_URL = "http://127.0.0.1:5000"

# Student ID range
LOW = 0
HIGH = 24575

# Requests configuration
NUM_THREADS = 50
READS = 10000
WRITES = 10000


def init(analysis_index, num_shards, num_replicas, num_servers):
    shards = []
    shard_size = (HIGH - LOW + 1) // num_shards
    for i in range(num_shards):
        shard = {
            "Stud_id_low": LOW + i * (shard_size),
            "Shard_id": str(i + 1),
            "Shard_size": shard_size
        }
        shards.append(shard)

    servers = {}
    shards_per_server = math.ceil((num_shards * num_replicas) / num_servers)
    for i in range(num_servers):
        servers[f"Server{i}"] = [str(j % num_shards + 1)
                                 for j in range(i, i + shards_per_server)]

    init_payload = {
        "N": num_servers,
        "schema": {
            "columns": ["Stud_id", "Stud_name", "Stud_marks"],
            "dtypes": ["Number", "String", "String"]
        },
        "shards": shards,
        "servers": servers
    }

    with open(f"Analysis/A{analysis_index}/init_payload.json", "w") as f:
        f.write(str(init_payload).replace("'", "\""))
    requests.post(f"{BASE_URL}/init", json=init_payload)


def write():
    # num_entries = random.randint(1, 10)
    num_entries = 2

    entries = []
    for _ in range(num_entries):
        entry = {
            "Stud_id": random.randint(LOW, HIGH),
            "Stud_name": "ABC",
            "Stud_marks": random.randint(0, 100),
        }
        entries.append(entry)

    request = {"data": entries}

    requests.post(f"{BASE_URL}/write", json=request)


def read():
    low = random.randint(LOW, HIGH)
    high = random.randint(low, HIGH)
    request = {
        "Stud_id": {"low": low, "high": high},
    }

    requests.post(f"{BASE_URL}/read", json=request)
    # response = requests.post(f"{BASE_URL}/read", json=request)
    # with open("Analysis/reads.txt", "a") as f:
    #     f.write(str(response.json()) + "\n")


def threader(num_times, func):
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = [executor.submit(func) for _ in range(num_times)]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    return time.time() - start_time


def analysis():
    return threader(WRITES, write), threader(READS, read), WRITES, READS


if __name__ == '__main__':
    print('Client is running')

    if len(sys.argv) < 2:
        print("Usage: python client.py <analysis_index>")
        sys.exit(1)

    analysis_index = int(sys.argv[1])

    if not os.path.exists(f"Analysis/A{analysis_index}"):
        os.makedirs(f"Analysis/A{analysis_index}")

    num_shards = 4 if len(sys.argv) <= 2 else int(sys.argv[2])
    num_replicas = 3 if len(sys.argv) <= 3 else int(sys.argv[3])
    num_servers = 6 if len(sys.argv) <= 4 else int(sys.argv[4])

    num_servers = max(num_servers, num_replicas)
    init(analysis_index, num_shards, num_replicas, num_servers)

    total_write_time, total_read_time, total_writes, total_reads = analysis()
    output = {
        "shards": num_shards,
        "replicas": num_replicas,
        "servers": num_servers,
        "read_time": total_read_time,
        "write_time": total_write_time,
        "writes": total_writes,
        "reads": total_reads
    }

    if (analysis_index > 1):
        with open(f"Analysis/A1/time.json", "r") as f:
            data = eval(f.read())
            output["write_speeddown"] = total_write_time / data["write_time"]
            output["read_speedup"] = data["read_time"] / total_read_time

    with open(f"Analysis/A{analysis_index}/time.json", "w") as f:
        f.write(str(output).replace("'", "\""))
