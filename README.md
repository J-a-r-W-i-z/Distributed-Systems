# Load Balancer

This Docker containerized load balancer is designed to efficiently distribute incoming requests among a set of maintained servers. It provides endpoints for adding new servers, removing existing servers, and retrieving details of existing servers. Additionally, a liveness checker thread monitors the health of maintained servers, taking appropriate actions in case of errors.

## Design Details

1. **Request Handling:**
   - Upon receiving a request, a new thread is assigned to handle the request.
   - A request object is created, including a unique request ID and client request IP and port.
   - The request is added to a consistent hashing data structure.
   - The load balancer waits for a server to get assigned for the specific request.
   - Upon assignment, the load balancer makes a GET request to the assigned server using its details.
   - The load balancer waits for the response and forwards it to the client.
   - If the response is not received (due to server crash, timeout, or other errors), the load balancer retries the request after waiting for a constant time.

2. **Assigner Thread:**
   - Activated when there is at least one pending request.
   - Assigns servers to requests when a timeout occurs or a fixed amount (e.g., 1000) of requests are in the consistent hashing data structure.
   - Locks the data structure.
   - Finds a server slot and assigns requests to that server.
   - Updates the assigner_map and generates a signal to wake up client request handler threads waiting for server assignment.
   - Removes assigned requests from the data structure and releases the lock.

3. **Liveness Checker Thread:**
   - Runs in a specified time interval.
   - Sends a heartbeat request to each server.
   - Checks for connection timeouts or server crash errors.
   - If a crash or fault is detected, removes the server information from all data structures.
   - If the number of active servers becomes less than the minimum requirements, spawns new servers.

## Design Details

- **Data Structures:**
  - Consistent Hashing Data Structure: Used for efficient assignment of requests to servers.
  - Assigner Map: Maintains the assignments made by the assigner thread.

- **Threads:**
  - Request Handler Threads: Handle incoming client requests.
  - Assigner Thread: Assigns servers to requests.
  - Liveness Checker Thread: Monitors the health of maintained servers.

- **Endpoints:**
  - `/add_server`: Add a new server to the load balancer.
  - `/remove_server`: Remove an existing server from the load balancer.
  - `/get_server_details`: Get details of existing servers.

## Building and Running the Docker Container

To build and run the Docker container, follow these steps:

1. Build the Docker image:
   ```bash
   docker build -t load-balancer .
