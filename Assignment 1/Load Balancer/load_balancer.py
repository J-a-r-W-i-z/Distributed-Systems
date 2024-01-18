import http.server
import socketserver
import os
import json
import random

class Server:
    def __init__(self, server_id,server_ip, server_port):
        self.id = server_id
        self.ip = server_ip
        self.port = server_port

class client_request:
    def __init__(self, client_ip, client_port):
        self.ip = client_ip
        self.port = client_port
        self.client_id = random.randint(1,1000000)
    

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/home':
            self.handle_home()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    
# Set up the server with the specified port (5000)
PORT = 5000
with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
    print(f"Server running on port {port}")
    httpd.serve_forever()
