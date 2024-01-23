from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import multiprocessing
from threading import Thread
import subprocess
import threading
import os
import json
import random
import time
import requests

# Set the server ID from the environment variable
N = os.environ.get('N', 'Unknown')
print("N = " + N)

MAX_TIME = 5
MIN_SERVERS = int(N)


class Server:
    def __init__(self, server_id, name, hostname, port):
        self.id = server_id
        self.name = name
        self.hostname = hostname
        self.port = port
        self.request_queue = []  # list of request assigned for this server


class client_request:
    def __init__(self, client_ip, client_port, client_id):
        self.ip = client_ip
        self.port = client_port
        self.id = client_id
        self.is_served = False


class ServerManager:
    available_ids = set()
    next_id = 1

    def generate_server_id(self):
        if ServerManager.available_ids:
            server_id = ServerManager.available_ids.pop()
        else:
            server_id = ServerManager.next_id
            ServerManager.next_id += 1
        return server_id

    def delete_server_id(self, server_id):
        ServerManager.available_ids.add(server_id)


total_live_servers = MIN_SERVERS  # total number of live servers
total_slots = 512  # total number of slots in the consistent hashing ring
num_virtual_servers = 9  # number of virtual servers per physical server
MAX_RETRY = 5
request_map = {}  # key: request_id, value: client_request
server_map = {}  # key: server_id, value: Server object


# key: server_id, value: list of slot numbers in the consistent hashing ring
server_slot_map = {}


# Data structutre to store the request and servers assigned to each slot in the consistent hashing ring
request_allocator = [None]*total_slots
request_allocator_lock = threading.Lock()


assigner_map = {}  # key: request_id, value: server object
assigner_map_lock = threading.Lock()
server_assignment_event = threading.Event()

current_unassigned_request = 0
current_unassigned_request_lock = threading.Lock()

TIME_LIMIT_FOR_SERVER_ALLOCATION = 0.01
MINMIMUM_REQUEST_ALLOCATION = 1000
min_req_allocation_event = threading.Event()


def get_request_id():  # generate unique request id
    number = random.randint(100000, 999999)
    while number in request_map:
        number = random.randint(100000, 999999)
    return number


# generate hash value and return slot number for the request
def get_request_slot(request_id):
    val = request_id*request_id + 2*request_id + 17
    return val % total_slots


# generate hash value and return slot number for the server
def get_server_slot(server_id, virtual_server_id):
    val = server_id*server_id + virtual_server_id * \
        virtual_server_id + 2*virtual_server_id + 25
    return (val*37) % total_slots


def worker_function(id):
    # Command to run
    command = f'sudo docker run --name web-server_{id} --network assignment1_myNetwork --network-alias web-server_{id} -e SERVER_ID={id} -p 500{id}:5000 web-server'
    res = os.popen(command).read()
    exit()


def spawn_server(id):
    child_process = multiprocessing.Process(target=worker_function, args=(id,))
    child_process.start()


def remove_server(container_name):
    os.system(
        f'sudo docker stop {container_name} && sudo docker rm {container_name}')

# liveness checker thread worker function


def liveness_checker():
    global total_live_servers
    while True:
        current_live_servers = total_live_servers
        inactive_server_ids = []
        for server_id, server in server_map.items():
            try:
                response = requests.get(
                    f'http://{server.ip}:{server.port}/heartbeat', timeout=MAX_TIME)

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
            remove_server(f'web-server_{server_id}')
            del server_map[server_id]  # point to be noted your honor

            for slot in server_slot_map[server_id]:
                with request_allocator_lock:
                    request_allocator[slot].remove(0)
            del server_slot_map[server_id]

        total_live_servers = current_live_servers

        # if the number of live servers are greater than 3, continue
        if total_live_servers >= MIN_SERVERS:
            time.sleep(3)
            continue

        for _ in range(1, MIN_SERVERS-total_live_servers+1):
            server_id = ServerManager().generate_server_id()

            # TODO: handle exceptiosn if time permits
            # spawn_server(server_id)
            server_ip = '127.0.0.1'
            server_port = 5000 + server_id
            server_map[server_id] = Server(
                server_id, server_ip, server_port)

            for j in range(1, num_virtual_servers+1):
                slot = get_server_slot(server_id, j)

                with request_allocator_lock:
                    start_pos = slot
                    while True:
                        if request_allocator[slot] == None:
                            request_allocator[slot] = [
                                server_map[server_id]]
                            server_slot_map[server_id].append(slot)
                            break

                        if type(request_allocator[slot][0]) != Server:
                            request_allocator[slot].insert(
                                0, server_map[server_id])
                            server_slot_map[server_id].append(slot)
                            break

                        slot = (slot+1) % total_slots
                        if slot == start_pos:
                            break

        total_live_servers = MIN_SERVERS
        time.sleep(3)

# worker function for assigner thread


def assigner():
    global current_unassigned_request

    while True:
        flag = False
        with current_unassigned_request_lock:
            if current_unassigned_request > 0:
                flag = True
        if flag:
            # print("Assigner thread is running")
            # wait for the request allocator data structure to be updated

            min_req_allocation_event.clear()
            min_req_allocation_event.wait(TIME_LIMIT_FOR_SERVER_ALLOCATION)
            # lock the request allocator data structure using mutex lock
            with request_allocator_lock:
                # find a slot which contains a server
                # print the request allocator data structure each server and each request individually
                # print("Request Allocator Data Structure")
                # for slot in range(0, total_slots):
                #     if request_allocator[slot] != None:
                #         print("\nSlot " + str(slot) + " : ",end=" ")
                #         for item in request_allocator[slot]:
                #             if type(item) == Server:
                #                 print("Server " + str(item.id),end=" ")
                #             else:
                #                 print("Request " + str(item.id),end=" ")
                # print("\nEnd of Request Allocator Data Structure")

                start_slot = 0
                for slot in range(0, total_slots):
                    if request_allocator[slot] != None:
                        if type(request_allocator[slot][0]) == Server:
                            start_slot = slot
                            break
                # traverse from start slot to assign requests to the next server(clockwise manner)
                curr_slot = start_slot
                req_list = []
                while True:
                    if request_allocator[curr_slot] != None:
                        if type(request_allocator[curr_slot][0]) == Server:
                            if len(req_list) > 0:
                                # assign the requests in req_list to the server in the current slot
                                server = request_allocator[curr_slot][0]
                                for req in req_list:
                                    with assigner_map_lock:
                                        assigner_map[req.id] = server
                                    print("Request " + str(req.id) +
                                          " is assigned to server " + str(server.id))
                                    # server.request_queue.append(req)
                                req_list = []
                            for i in range(1, len(request_allocator[curr_slot])):
                                req_list.append(
                                    request_allocator[curr_slot][i])
                        else:
                            req_list.extend(request_allocator[curr_slot])
                    curr_slot = (curr_slot+1) % total_slots
                    if curr_slot == start_slot:
                        break
                for req in req_list:
                    with assigner_map_lock:
                        assigner_map[req.id] = request_allocator[start_slot][0]
                with current_unassigned_request_lock:
                    current_unassigned_request=0
                server_assignment_event.set()
                server_assignment_event.clear()

                # remove the requests from the request allocator data structure(except servers)
                for slot in range(0, total_slots):
                    if request_allocator[slot] != None:
                        if type(request_allocator[slot][0]) != Server:
                            request_allocator[slot] = None
                        else:
                            request_allocator[slot] = [
                                request_allocator[slot][0]]


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global current_unassigned_request
        global total_live_servers

        if self.path == '/home':
            # time.sleep(30)
            client_ip, client_port = self.client_address
            req = client_request(client_ip, client_port, get_request_id())
            request_map[req.id] = req

            for __ in range(0, MAX_RETRY):
                print("Request " + str(req.id) + " is received")
                slot = get_request_slot(req.id)

                # lock the request allocator data structure using mutex lock
                with request_allocator_lock:
                    if request_allocator[slot] == None:
                        request_allocator[slot] = [req]
                    else:
                        # put the request object in the slot
                        request_allocator[slot].append(req)
                with current_unassigned_request_lock:
                    current_unassigned_request += 1
                    if current_unassigned_request >= MINMIMUM_REQUEST_ALLOCATION:
                        min_req_allocation_event.set()
                        min_req_allocation_event.clear()
                # release the mutex lock
                server_assignment_event.clear()
                server_assignment_event.wait()
                print("Request " + str(req.id) + " is assigned to slot " + str(slot))

                # wait for the server assignment event
                server = None
                with assigner_map_lock:
                    if req.id in assigner_map:
                        server = assigner_map[req.id]
                    else:
                        print("Request " + str(req.id)+" Not found")
                        continue
                    
                print("Request " + str(req.id) + " is assigned to server " + str(server.id))
                try:
                    response = requests.get(
                        f'http://{server.hostname}:5000/home')
                    # Forward the response as is
                    self.send_response(response.status_code)
                    for key, value in response.headers.items():
                        self.send_header(key, value)
                    self.end_headers()
                    self.wfile.write(response.content)
                    with assigner_map_lock:
                        del assigner_map[req.id]
                    break

                except requests.exceptions.RequestException as e:
                    # Handle exceptions (e.g., connection error, timeout)
                    # time.sleep(2)
                    print(f"Request failed with exception: {e}")
                    with assigner_map_lock:
                        del assigner_map[req.id]
                except Exception as e:
                    # Handle other exceptions
                    # time.sleep(2)
                    print(f"An unexpected error occurred: {e}")
                    with assigner_map_lock:
                        del assigner_map[req.id]

        elif self.path == '/rep':
            response_data = {
                # TODO: give host names in the place of replicas
                "message": {
                    "N": total_live_servers,
                    "replicas": [f"Server {server_id}" for server_id in server_map.keys()]
                },
                "status": "successful"
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())

        elif self.path == '/add':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)
            n, hostnames = data['n'], data['hostnames']
            for hostname in hostnames:
                pass

        elif self.path == '/rm':
            pass

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')


# Set up the server with the specified port (5000)
PORT = 5000


def run():
    # initialize N servers
    global total_live_servers
    for _ in range(1, total_live_servers+1):
        server_id = ServerManager().generate_server_id()
        hostname = "server_"+str(server_id)
        port = 5000 + server_id
        name = "web_server_"+str(server_id)
        spawn_server(server_id, name, hostname, port)
        server_map[server_id] = Server(server_id, name, hostname, port)
        print("Server " + str(server_id) +
              " is running on port " + str(port))

    print("All servers started")

    for _id in server_map.keys():
        for j in range(1, num_virtual_servers+1):
            slot = get_server_slot(_id, j)
            # do probing
            while request_allocator[slot] != None:
                slot = (slot+1) % total_slots
            request_allocator[slot] = [server_map[_id]]
            if _id not in server_slot_map:
                server_slot_map[_id] = []
            server_slot_map[_id].append(slot)  # server slot
            # print("Server " + str(_id) + " is assigned to slot " + str(slot))

    # create assigner thread
    assigner_thread = Thread(target=assigner)  # create thread
    assigner_thread.start()  # start the thread

    # create liveness checker thread
    # liveness_checker_thread = Thread(target=liveness_checker)  # create thread
    # liveness_checker_thread.start()  # start the thread

    # run the load balancer
    print("Runninggggg")
    server = ThreadingHTTPServer(("", PORT), RequestHandler)
    server.serve_forever()


############################### Docker Functions ##################################

def worker_function(id, name, hostname,port):
    # Command to run
    command = f'sudo docker run --name {name} --network assignment1_myNetwork --network-alias web-server_{id}  --hostname {hostname} -e SERVER_ID={id} -p {port}:5000 web-server'
    res = os.popen(command).read()
    exit()

def spawn_server(id, name, hostname, port):
    print("Spawningggggggg")
    command = f'sudo docker run --name {name} --network assignment1_myNetwork --network-alias web-server_{id}  --hostname {hostname} -e SERVER_ID={id} -p {port}:5000 web-server'
    # res = os.popen(command).read()
    subprocess.Popen(command, shell=True)
    # child_process = multiprocessing.Process(target=worker_function, args=(id,name,hostname,port))
    # child_process.start()

def remove_server(container_name):
    os.system(f'sudo docker stop {container_name} && sudo docker rm {container_name}')


if __name__ == '__main__':
    run()
