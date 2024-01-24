from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from threading import Thread
from time import sleep
import subprocess
import os
import json
import random
import requests
import multiprocessing


# Set the server ID from the environment variable
N = os.environ.get('N', 'Unknown')
print("N = " + N)
N = int(N)

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
    
total_live_servers = 0 # total number of live servers
gloal_request_id = 0
total_slots= 512 # total number of slots in the consistent hashing ring
num_virtual_servers = 9 # number of virtual servers per physical server

server_list = [] # list of Server objects
request_map = {} # key: request_id, value: client_request
server_map = {} # key: server_id, value: Server object



request_allocator =[None]*total_slots # Data structutre to store the request and servers assigned to each slot in the consistent hashing ring




def get_request_id(): # generate unique request id
    global global_request_id
    global_request_id += 1
    return global_request_id

def get_request_slot(request_id): # generate hash value and return slot number for the request
    val = request_id*request_id + 2*request_id + 17
    return val % total_slots

def get_server_slot(server_id, virtual_server_id): # generate hash value and return slot number for the server
    val = server_id*server_id + virtual_server_id*virtual_server_id + 2*virtual_server_id + 25
    return val % total_slots

def serve_client_request(client_ip, client_port):
    req = client_request(client_ip,client_port, get_request_id())
    request_map[req.id] = req
    slot = get_request_slot(req.id)

    pos=slot

    while(request_allocator[pos] != None ): # find the next free slot( linear-probing)
        pos+=1
        if pos==slot:
            print("Cannot serve request!! No Free slots")
            return
    
    request_allocator[pos] = req # put the request object in the slot


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/home':
            client_ip, client_port = self.client_address
            serve_client_request(client_ip,client_port)

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
    server = ThreadingHTTPServer(("", port), RequestHandler)
    server.serve_forever()



def worker_function(id):
    # Command to run
    command = f'sudo docker run --name web-server_{id} --network assignment1_myNetwork --network-alias web-server_{id} --hostname server_{id} -e SERVER_ID={id} -p {5000+id}:5000 web-server'
    res = os.popen(command).read()
    exit()

def spawn_server(id):
    child_process = multiprocessing.Process(target=worker_function, args=(id,))
    child_process.start()

def remove_server(container_name):
    os.system(f'sudo docker stop {container_name} && sudo docker rm {container_name}')


if __name__ == '__main__':
    print("Controller Called!!")

    #Initialize N servers
    for i in range(N):
        print(f"Spawing server {i+1}...")
        spawn_server(i+1)

    for i in range(N):
        print(f"Sending Get request to Server {i+1}...")
        url=f"http://server_{i+1}:5000/home"
        response = requests.get(url)
        print(response.text)


    sleep(1000)


