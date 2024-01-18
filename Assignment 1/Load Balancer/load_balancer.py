from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
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

    pos=slot #[ (5,s1),(6,s2),(7,s3),(8,s4),(10,r1),(11,s7),(12,r2),(13,s9)]

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


if __name__ == '__main__':
    run()
