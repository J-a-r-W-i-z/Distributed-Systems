from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import multiprocessing
from threading import Thread
import threading
import os
import json
import random
import requests

class Server:
    def __init__(self, server_id,server_ip, server_port):
        self.id = server_id
        self.ip = server_ip
        self.port = server_port
        self.request_queue = [] # list of request assigned for this server

class client_request: 
    def __init__(self, client_ip, client_port,client_id):
        self.ip = client_ip
        self.port = client_port
        self.id = client_id
        self.is_served = False
    
total_live_servers = 3 # total number of live servers
current_unserved_request = 0
total_slots= 512 # total number of slots in the consistent hashing ring
num_virtual_servers = 9 # number of virtual servers per physical server
MAX_RETRY = 3

server_list = [] # list of Server objects
request_map = {} # key: request_id, value: client_request
server_map = {} # key: server_id, value: Server object



request_allocator =[None]*total_slots # Data structutre to store the request and servers assigned to each slot in the consistent hashing ring
request_allocator_lock = threading.Lock()


assigner_map={} # key: request_id, value: server object
server_assignment_event = threading.Event()



def get_request_id(): # generate unique request id
    number = random.randint(100000, 999999)
    while number in request_map:
        number = random.randint(100000, 999999)
    return number
    

def get_request_slot(request_id): # generate hash value and return slot number for the request
    val = request_id*request_id + 2*request_id + 17
    return val % total_slots

def get_server_slot(server_id, virtual_server_id): # generate hash value and return slot number for the server
    val = server_id*server_id + virtual_server_id*virtual_server_id + 2*virtual_server_id + 25
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
    os.system(f'sudo docker stop {container_name} && sudo docker rm {container_name}')



class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/home':
            client_ip, client_port = self.client_address
            req = client_request(client_ip,client_port, get_request_id())
            request_map[req.id] = req

            for tries in range(0, MAX_RETRY):
                slot = get_request_slot(req.id)

                # lock the request allocator data structure using mutex lock
                with request_allocator_lock:
                    request_allocator[slot].add(req) # put the request object in the slot
                # release the mutex lock
                print("Request " + str(req.id) + " is assigned to slot " + str(slot))

                # wait for the server assignment event
                server_assignment_event.wait()
                # make get request to the assigned server
                server = assigner_map[req.id]
                print("Request " + str(req.id) + " is assigned to server " + str(server.id))
                try:
                    response = requests.get(f'http://{server.ip}:{server.port}/home')
                    # Forward the response as is
                    self.send_response(response.status_code)
                    for key, value in response.headers.items():
                        self.send_header(key, value)
                    self.end_headers()
                    self.wfile.write(response.content)

                    # Check if the server returned a successful response
                    if response.status_code != 200:
                        print(f"Request failed with status code: {response.status_code}")

                except requests.exceptions.RequestException as e:
                    # Handle exceptions (e.g., connection error, timeout)
                    print(f"Request failed with exception: {e}")
                except Exception as e:
                    # Handle other exceptions
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
    for i in range(1,total_live_servers+1):
        spawn_server(i)
        server_id = i
        server_ip = '127.0.0.1'
        server_port = 5000 + i
        server_list.append(Server(server_id,server_ip,server_port))
        server_map[server_id] = server_list[i-1]
        print("Server " + str(server_id) + " is running on port " + str(server_port))
    
    # Put into consistent hashing data structure
    for i in range(1,total_live_servers+1):
        for j in range(1,num_virtual_servers+1):
            slot = get_server_slot(i,j)
            # do probing 
            while request_allocator[slot] != None:
                slot = (slot+1)%total_slots
            request_allocator[slot] = [server_map[i]]
            print("Server " + str(i) + " is assigned to slot " + str(slot))
    
    # create assigner thread

    # create liveness checker thread

    # run the load balancer
    

    server = ThreadingHTTPServer(("", port), RequestHandler)
    server.serve_forever()


if __name__ == '__main__':
    run()
