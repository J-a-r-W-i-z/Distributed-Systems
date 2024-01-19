from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import os
import json
import time

# Set the server ID from the environment variable
server_id = os.environ.get('SERVER_ID', 'Unknown')

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/home':
            self.handle_home()
        elif self.path == '/heartbeat':
            self.handle_heartbeat()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def handle_home(self):
        response_data = {
            "message": f"Hello from Server: {server_id}",
            "status": "successful"
        }
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode())

    def handle_heartbeat(self):
        self.send_response(200)
        self.end_headers()

# Set up the server with the specified port (5000)
port = 5000

def run():
    print("Server running...")
    server = ThreadingHTTPServer(("", port), RequestHandler)
    server.serve_forever()


if __name__ == '__main__':
    run()
