from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import threading
import json
import random
import time
import requests
import os
import subprocess
import logging

N = os.environ.get("N", "Unknown")

MAX_TIMEOUT = 5
SPAWN_LATENCY = 1
LIVENESS_SLEEP_TIME = 3
MIN_SERVERS = int(N)
MAX_RETRY = 5
RETRY_WAIT_TIME = 4
TOTAL_SLOTS = 512
NUM_VIRTUAL_SERVERS = 9
TIME_LIMIT_FOR_SERVER_ALLOCATION = 1
MINMIMUM_REQUEST_ALLOCATION = 1000


class Server:
    def __init__(self, server_id, server_name, hostname, server_port):
        self.id = server_id
        self.name = server_name
        self.hostname = hostname
        self.port = server_port
        self.request_queue = []  # list of requests assigned to this server


class ClientRequest:
    def __init__(self, client_ip, client_port, client_id):
        self.ip = client_ip
        self.port = client_port
        self.id = client_id
        self.is_served = False


class ServerManager:
    available_ids = set()
    next_id = 1

    @classmethod
    def generate_server_id(cls):
        if cls.available_ids:
            server_id = cls.available_ids.pop()
        else:
            server_id = cls.next_id
            cls.next_id += 1
        return server_id

    @classmethod
    def delete_server_id(cls, server_id):
        cls.available_ids.add(server_id)


class LoadBalancer:
    def __init__(self):
        self.request_map = {}
        self.server_map = {}
        self.server_map_lock = threading.Lock()
        self.server_slot_map = {}
        self.server_slot_map_lock = threading.Lock()
        self.request_allocator = [None] * TOTAL_SLOTS
        self.request_allocator_lock = threading.Lock()
        self.assigner_map = {}
        self.assigner_map_lock = threading.Lock()
        self.server_assignment_event = threading.Event()
        self.current_unassigned_request = 0
        self.current_unassigned_request_lock = threading.Lock()
        self.min_req_allocation_event = threading.Event()

    def get_request_id(self):
        number = random.randint(100000, 999999)
        while number in self.request_map:
            number = random.randint(100000, 999999)
        return number

    def get_request_slot(self, request_id):
        val = request_id * request_id + 2 * request_id + 17
        return val % TOTAL_SLOTS

    def get_server_slot(self, server_id, virtual_server_id):
        val = server_id * server_id + virtual_server_id * \
            virtual_server_id + 2 * virtual_server_id + 25
        return (val * 37) % TOTAL_SLOTS

    def spawn_server(self, id, name, hostname, port):
        command = f"sudo docker run --name {name} --network assignment1_myNetwork --network-alias {name}  --hostname {hostname} -e SERVER_ID={id} -p {port}:5000 web-server"
        # res = os.popen(command).read()
        subprocess.Popen(command, shell=True)
        # child_process = multiprocessing.Process(target=worker_function, args=(id,name,hostname,port))
        # child_process.start()

    def remove_server(self, container_name):
        os.system(
            f"sudo docker stop {container_name} && sudo docker rm {container_name}")

    def virtualize_servers(self, server_id):
        for j in range(1, NUM_VIRTUAL_SERVERS + 1):
            slot = self.get_server_slot(server_id, j)

            with self.request_allocator_lock:
                start_pos = slot
                while True:
                    if self.request_allocator[slot] is None or len(self.request_allocator[slot]) == 0:
                        with self.server_map_lock:
                            self.request_allocator[slot] = [
                                self.server_map[server_id]]

                        with self.server_slot_map_lock:
                            if server_id not in self.server_slot_map:
                                self.server_slot_map[server_id] = []
                            self.server_slot_map[server_id].append(slot)
                            break

                    if type(self.request_allocator[slot][0]) != Server:
                        with self.server_map_lock:
                            self.request_allocator[slot].insert(
                                0, self.server_map[server_id])

                        with self.server_slot_map_lock:
                            if server_id not in self.server_slot_map:
                                self.server_slot_map[server_id] = []
                            self.server_slot_map[server_id].append(slot)
                        break

                    slot = (slot + 1) % TOTAL_SLOTS
                    if slot == start_pos:
                        break

    def create_server_intance(self, server_id, hostname=None):
        server_name = f"web_server_{server_id}"
        if hostname is None:
            hostname = f"server_{server_id}"
        server_port = 5000 + server_id
        self.spawn_server(server_id, server_name, hostname, server_port)
        server = Server(server_id, server_name, hostname, server_port)
        with self.server_map_lock:
            self.server_map[server_id] = server

    def remove_server_instance(self, server_id):
        with self.server_map_lock:
            self.remove_server(self.server_map[server_id].name)
            del self.server_map[server_id]
            ServerManager.delete_server_id(server_id)

        with self.server_slot_map_lock:
            for slot in self.server_slot_map[server_id]:
                with self.request_allocator_lock:
                    self.request_allocator[slot].pop(0)
            del self.server_slot_map[server_id]

    def liveness_checker(self):
        while True:
            time.sleep(LIVENESS_SLEEP_TIME)

            with self.server_map_lock:
                current_live_servers = len(self.server_map)
                inactive_server_ids = []

                for server_id, server in self.server_map.items():
                    try:
                        response = requests.get(
                            f"http://{server.hostname}:5000/heartbeat", timeout=MAX_TIMEOUT)

                        if response.status_code != 200:
                            inactive_server_ids.append(server_id)
                            current_live_servers -= 1
                    except requests.exceptions.RequestException as e:
                        print(f"Request failed with exception: {e}")
                        inactive_server_ids.append(server_id)
                        current_live_servers -= 1
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")
                        inactive_server_ids.append(server_id)
                        current_live_servers -= 1

            for server_id in inactive_server_ids:
                self.remove_server_instance(server_id)

            if current_live_servers >= MIN_SERVERS:
                continue

            for _ in range(1, MIN_SERVERS - current_live_servers + 1):
                server_id = ServerManager.generate_server_id()
                self.create_server_intance(server_id)
                self.virtualize_servers(server_id)

    def assigner(self):
        while True:
            flag = False
            with self.current_unassigned_request_lock:
                if self.current_unassigned_request > 0:
                    flag = True
            if flag:
                # print("Assigner is running")
                # wait for the request allocator data structure to be updated

                self.min_req_allocation_event.clear()
                self.min_req_allocation_event.wait(
                    TIME_LIMIT_FOR_SERVER_ALLOCATION)

                # Lock the request allocator data structure using mutex lock
                with self.request_allocator_lock:
                    start_slot = -1
                    for slot in range(0, TOTAL_SLOTS):
                        if self.request_allocator[slot] is None or len(self.request_allocator[slot]) == 0:
                            continue

                        if type(self.request_allocator[slot][0]) == Server:
                            start_slot = slot
                            break

                    if start_slot == -1:
                        continue

                    # traverse from the start slot to find the next server slot
                    curr_slot = start_slot
                    req_list = []
                    while True:
                        if self.request_allocator[curr_slot] is not None and len(self.request_allocator[curr_slot]) > 0:
                            if type(self.request_allocator[curr_slot][0]) == Server:
                                if len(req_list) > 0:
                                    server = self.request_allocator[curr_slot][0]
                                    for req in req_list:
                                        with self.assigner_map_lock:
                                            self.assigner_map[req.id] = server
                                        print("Request " + str(req.id) +
                                              " is assigned to server " + str(server.id))
                                    req_list = []
                                for i in range(1, len(self.request_allocator[curr_slot])):
                                    req_list.append(
                                        self.request_allocator[curr_slot][i])
                            else:
                                req_list.extend(
                                    self.request_allocator[curr_slot])
                        curr_slot = (curr_slot + 1) % TOTAL_SLOTS
                        if curr_slot == start_slot:
                            break
                    for req in req_list:
                        with self.assigner_map_lock:
                            self.assigner_map[req.id] = self.request_allocator[start_slot][0]
                    with self.current_unassigned_request_lock:
                        self.current_unassigned_request = 0
                    self.server_assignment_event.set()
                    self.server_assignment_event.clear()

                    # remove the requests from the request allocator data structure
                    for slot in range(0, TOTAL_SLOTS):
                        if self.request_allocator[slot] is not None and len(self.request_allocator[slot]) > 0:
                            if type(self.request_allocator[slot][0]) != Server:
                                self.request_allocator[slot] = None
                            else:
                                self.request_allocator[slot] = [
                                    self.request_allocator[slot][0]]

    def run(self, port):
        for _ in range(1, MIN_SERVERS + 1):
            server_id = ServerManager.generate_server_id()
            self.create_server_intance(server_id)

            for j in range(1, NUM_VIRTUAL_SERVERS + 1):
                slot = self.get_server_slot(server_id, j)

                # probing to find the next empty slot
                while self.request_allocator[slot] is not None:
                    slot = (slot + 1) % TOTAL_SLOTS

                self.request_allocator[slot] = [self.server_map[server_id]]

                if server_id not in self.server_slot_map:
                    self.server_slot_map[server_id] = []
                self.server_slot_map[server_id].append(slot)
                # print("Server " + str(server_id) + " is assigned to slot " + str(slot))

        assigner_thread = threading.Thread(target=self.assigner)
        assigner_thread.start()

        liveness_checker_thread = threading.Thread(
            target=self.liveness_checker)
        liveness_checker_thread.start()

        handler = lambda *args, **kwargs: RequestHandler(
            *args, load_balancer=self, **kwargs)
        server = ThreadingHTTPServer(("", port), handler)
        server.serve_forever()


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, load_balancer, **kwargs):
        self.lb = load_balancer
        super().__init__(*args, **kwargs)

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length).decode("utf-8")

        if self.path == "/add":
            data = json.loads(post_data)
            n, hostnames = data["n"], data["hostnames"]

            if (n < len(hostnames)):
                self.post_error_handler()
                return

            for i in range(n):
                server_id = ServerManager.generate_server_id()
                hostname = None if i >= len(hostnames) else hostnames[i]
                self.lb.create_server_intance(server_id, hostname)
                time.sleep(SPAWN_LATENCY)
                self.lb.virtualize_servers(server_id)

            self.send_status_of_replicas()

        elif self.path == "/rm":
            data = json.loads(post_data)
            n, hostnames = data["n"], data["hostnames"]

            if (n < len(hostnames)):
                self.post_error_handler()
                return

            for hostname in hostnames:
                with self.lb.server_map_lock:
                    for server_id, server in self.lb.server_map.items():
                        if server.hostname != hostname:
                            continue

                        self.lb.remove_server_instance(server_id)
                        n -= 1
                        break

            for _ in range(n):
                with self.lb.server_map_lock:
                    server_id = random.choice(list(self.lb.server_map.keys()))
                self.lb.remove_server_instance(server_id)

            self.send_status_of_replicas()

    def do_GET(self):
        if self.path == "/rep":
            self.send_status_of_replicas()
            return

        client_ip, client_port = self.client_address
        req = ClientRequest(client_ip, client_port,
                            self.lb.get_request_id())
        self.lb.request_map[req.id] = req

        for __ in range(0, MAX_RETRY):
            # print("Request " + str(req.id) + " is received")
            slot = self.lb.get_request_slot(req.id)

            # lock the request allocator data structure using mutex lock
            with self.lb.request_allocator_lock:
                if self.lb.request_allocator[slot] is None:
                    self.lb.request_allocator[slot] = []
                self.lb.request_allocator[slot].append(req)
            with self.lb.current_unassigned_request_lock:
                self.lb.current_unassigned_request += 1
                if self.lb.current_unassigned_request >= MINMIMUM_REQUEST_ALLOCATION:
                    self.lb.min_req_allocation_event.set()
                    self.lb.min_req_allocation_event.clear()
            # release the mutex lock
            self.lb.server_assignment_event.clear()
            self.lb.server_assignment_event.wait()
            # print("Request " + str(req.id) +
            #       " is assigned to slot " + str(slot))

            # wait for the server assignment event
            server = None
            with self.lb.assigner_map_lock:
                if req.id in self.lb.assigner_map:
                    server = self.lb.assigner_map[req.id]
                else:
                    print("Request " + str(req.id)+" Not found")
                    continue

            # print("Request " + str(req.id) +
            #       " is assigned to server " + str(server.id))
            try:
                response = requests.get(
                    f"http://{server.hostname}:5000{self.path}")
                self.send_response(response.status_code)
                for key, value in response.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.content)
                with self.lb.assigner_map_lock:
                    del self.lb.assigner_map[req.id]
                break

            except requests.exceptions.RequestException as e:
                # Handle exceptions (e.g., connection error, timeout)
                print(f"Request failed with exception: {e}")
                with self.lb.assigner_map_lock:
                    del self.lb.assigner_map[req.id]
                time.sleep(RETRY_WAIT_TIME)
            except Exception as e:
                # Handle other exceptions
                print(f"An unexpected error occurred: {e}")
                with self.lb.assigner_map_lock:
                    del self.lb.assigner_map[req.id]
                time.sleep(RETRY_WAIT_TIME)

    def post_error_handler(self):
        response_data = {
            "message": "<Error> Length of hostname list is more than newly added instances",
            "status": "failure"
        }
        self.send_response(400)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode())

    def send_status_of_replicas(self):
        with self.lb.server_map_lock:
            response_data = {
                "message": {
                    "N": len(self.lb.server_map),
                    "replicas": [server.hostname for server in self.lb.server_map.values()]
                },
                "status": "successful"
            }
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode())


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    logging.getLogger('http.server').setLevel(logging.ERROR)

    port = 5000
    load_balancer = LoadBalancer()
    load_balancer.run(port)
