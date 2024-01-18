import http.server
import socketserver
from threading import Thread
import os
import json
import random

class Server:
    def __init__(self, server_id,server_ip, server_port):
        self.id = server_id
        self.ip = server_ip
        self.port = server_port
        self.request_queue = [] # list of request assigned for this server

class client_request: 
    def __init__(self, client_ip, client_port):
        self.ip = client_ip
        self.port = client_port
        self.client_id = random.randint(1,1000000)
    
total_live_servers = 0 # total number of live servers
gloal_request_id = 0
total_slots= 512 # total number of slots in the consistent hashing ring
num_virtual_servers = 9 # number of virtual servers per physical server

server_list = [] # list of Server objects
request_map = {} # key: request_id, value: client_request
server_map = {} # key: server_id, value: Server object

request_allocator =[]*total_slots # Data structutre to store the request and servers assigned to each slot in the consistent hashing ring




def get_request_id(): # generate unique request id
    global global_request_id
    global_request_id += 1
    return global_request_id

def get_request_hash(request_id): # generate hash value for the request
    val = request_id*request_id +2*request_id+17
    return val % total_slots


def serve_client_request():
    pass

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/home':
            Thread(target=serve_client_request).start()


        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    


    
# Set up the server with the specified port (5000)
PORT = 5000
with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
    print(f"Server running on port {port}")
    httpd.serve_forever()
