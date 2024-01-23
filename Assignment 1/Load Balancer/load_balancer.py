from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import multiprocessing
from threading import Thread
import threading
import os
import json
import random
import time
import requests


class Server:
    def __init__(self, server_id, server_ip, server_port):
        self.id = server_id
        self.ip = server_ip
        self.port = server_port
        self.request_queue = []  # list of request assigned for this server


class client_request:
    def __init__(self, client_ip, client_port, client_id):
        self.ip = client_ip
        self.port = client_port
        self.id = client_id
        self.is_served = False


MAX_TIME = 2
MIN_SERVERS = 3
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
    return val % total_slots


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
            del server_map[server_id] # point to be noted your honor

            for slot in server_slot_map[server_id]:
                with request_allocator_lock:
                    request_allocator[slot].remove(0)
            del server_slot_map[server_id]

        total_live_servers = current_live_servers
        # if number of live servers is less than 3, spawn new servers
        
                
        time.sleep(3)

# worker function for assigner thread
def assigner():
    while True:
        flag = False
        with current_unassigned_request_lock:
            if current_unassigned_request > 0:
                flag = True
        if flag:
            # wait for the request allocator data structure to be updated
            min_req_allocation_event.wait(TIME_LIMIT_FOR_SERVER_ALLOCATION)
            # lock the request allocator data structure using mutex lock
            with request_allocator_lock:
                # find a slot which contains a server
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
                                    assigner_map[req.id] = server
                                    server.request_queue.append(req)
                                req_list = []
                                for i in range(1,len(request_allocator[curr_slot])):
                                    req_list.append(request_allocator[curr_slot][i])
                        else:
                            req_list.extend(request_allocator[curr_slot])
                    curr_slot = (curr_slot+1) % total_slots
                    if curr_slot == start_slot:
                        break
                for req in req_list:
                    assigner_map[req.id] = request_allocator[start_slot][0]
                server_assignment_event.set()

                # remove the requests from the request allocator data structure(except servers)
                for slot in range(0, total_slots):
                    if request_allocator[slot] != None:
                        if type(request_allocator[slot][0]) != Server:
                            request_allocator[slot] = None
                        else:
                            request_allocator[slot] = [request_allocator[slot][0]]

                   
                            
                

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/home':
            client_ip, client_port = self.client_address
            req = client_request(client_ip, client_port, get_request_id())
            request_map[req.id] = req

            for __ in range(0, MAX_RETRY):
                slot = get_request_slot(req.id)

                # lock the request allocator data structure using mutex lock
                with request_allocator_lock:
                    if request_allocator[slot] == None:
                        request_allocator[slot] = [req]
                    else:
                        request_allocator[slot].append(req) # put the request object in the slot

                with current_unassigned_request_lock:
                    current_unassigned_request+=1
                    if current_unassigned_request >= MINMIMUM_REQUEST_ALLOCATION:
                        min_req_allocation_event.set()
                # release the mutex lock
                print("Request " + str(req.id) + " is assigned to slot " + str(slot))

                # wait for the server assignment event
                server_assignment_event.wait()
                # make get request to the assigned server
                server = assigner_map[req.id]
                with current_unassigned_request_lock:
                    current_unassigned_request-=1
                        
                print("Request " + str(req.id) + " is assigned to server " + str(server.id))

                try:
                    response = requests.get(f'http://{server.ip}:{server.port}/home')
                    # Forward the response as is
                    self.send_response(response.status_code)
                    for key, value in response.headers.items():
                        self.send_header(key, value)
                    self.end_headers()
                    self.wfile.write(response.content)
                    


                except requests.exceptions.RequestException as e:
                    # Handle exceptions (e.g., connection error, timeout)
                    # time.sleep(2) 
                    print(f"Request failed with exception: {e}")
                except Exception as e:
                    # Handle other exceptions
                    # time.sleep(2)
                    print(f"An unexpected error occurred: {e}")

        elif self.path == '/rep':
            pass

        elif self.path == '/add':
            pass

        elif self.path == '/rm':
            pass

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')


# Set up the server with the specified port (5000)
port = 5000


def run():
    # initialize N servers
    for i in range(1, total_live_servers+1):
        # spawn_server(i)
        server_id = i
        server_ip = '127.0.0.1'
        # add host name
        server_port = 5000 + i
        server_map[server_id] = Server(server_id, server_ip, server_port)
        print("Server " + str(server_id) +
              " is running on port " + str(server_port))

    # Put into consistent hashing data structure
    for i in range(1, total_live_servers+1):
        for j in range(1, num_virtual_servers+1):
            slot = get_server_slot(i, j)
            # do probing
            while request_allocator[slot] != None:
                slot = (slot+1) % total_slots
            request_allocator[slot] = [server_map[i]]
            server_slot_map[i].append(slot)  # server slot
            print("Server " + str(i) + " is assigned to slot " + str(slot))

    # create assigner thread
    assigner_thread = Thread(target=assigner) # create thread
    assigner_thread.start() # start the thread

    # create liveness checker thread
    liveness_checker_thread = Thread(target=liveness_checker) # create thread
    liveness_checker_thread.start() # start the thread

    
    # run the load balancer

    server = ThreadingHTTPServer(("", port), RequestHandler)
    server.serve_forever()


if __name__ == '__main__':
    run()
