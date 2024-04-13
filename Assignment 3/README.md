# Assignment 3 README

## Overview
This assignment aims to implement a distributed system that implements Write-Ahead Logging (WAL) mechanism for maintaining consistency among the replicas of the shards that are distributed among various servers. In this readme, we will discuss the system design, data structures, and algorithms used in the implementation.

## System Design

### **Caching Tables for Faster Access:**

1. **Identifying Frequently Used Data**: Analyze the application's usage patterns and identify data that is frequently accessed or queried by multiple users. This includes the information of the shard-server mappings, server hostnames, shard meta data etc.

2. **Cache Initialization**: Load the identified data from the MySQL tables into an in-memory data structure when the application starts or on-demand. This can be done at the time of initialization of meta data tables and while writing data into the tables.

### **Locking Mechanism for Reader-Writer Problem:**

In the context of concurrent programming, the reader-writer problem involves managing access to a shared resource (such as data stored in memory or a database) by multiple threads that may either read or write to the resource. The objective is to ensure that:

- Multiple threads can read the resource simultaneously without interfering with each other (reader concurrency).
- Only one thread can write to the resource at a time, and during a write operation, no other thread (readers or writers) can access the resource (writer exclusion).

#### Read and Write Locks

- **Read Lock**: Allows multiple clients to read the resource at the same time.
- **Write Lock**: Allows only one client to write to the resource at a time.

#### Reading Task:

1. Acquire the read_count_lock.
2. Increment the read_count.
3. If the read_count is equal to 1 (i.e., the first reader), acquire the write lock to prevent writers from accessing the resource simultaneously with readers.
4. Release the read_count_lock to allow other threads to access the read_count safely.
5. Read the data from the shared resource.
6. Acquire the read_count_lock again.
7. Decrement the read_count.
8. If the read_count is 0 (i.e., no more readers), release the write lock to allow writers to access the resource.
9. Release the read_count_lock.

#### Writing Task:

1. Acquire the write lock to ensure exclusive access to the resource.
2. Write the data to the shared resource.
3. Release the write lock to allow other threads (both readers and writers) to access the resource.

By implementing these steps, we ensure that reader threads can access the shared resource concurrently while preventing writer threads from accessing it simultaneously to maintain data integrity.



### **Efficient Request Allotment Mechanism:**

- Maintaining Sorted Server Positions: To implement efficient request allotment, a list containing server positions in the consistent hashing data structure is maintained in sorted order. This list allows for quick lookup of servers based on hash values.

- Finding Slot for Request: When a request is received, the algorithm finds the slot for the request in logarithmic time complexity (logN) by finding the upper bound of the hash value in the sorted list of server positions. This upper bound represents the server closest to the hash value on the hash ring.

- Allotting Request to Server: Once the slot for the request is determined, the algorithm assigns the request to the corresponding server based on the position found in the sorted list. This server becomes responsible for handling the request.


### **Connection Pooling:**
Connection pooling is a technique used to manage and reuse database connections efficiently. Instead of creating a new database connection for each request, connections are pooled and reused whenever possible. Key aspects of connection pooling in the code include:

- sql_connection_pool: This global variable represents a pool of database connections to the MySQL server. Connections are established and added to the pool during system initialization.

- Connection Reuse: When a thread needs to execute a database query, it retrieves a connection from the connection pool. After executing the query, the connection is returned to the pool for reuse by other threads. This minimizes the overhead associated with establishing new connections for each query.

- Connection Management: The connection pool manages the lifecycle of database connections, including establishing new connections, recycling idle connections, and closing connections that have been idle for too long. This ensures optimal utilization of database resources and improves overall system performance.

### **Shard Manager - Load Balancer Consistency**

There are a lot of functionalities in shard manager and load balancer that need some common data like server to hostname mapping, server to shard mapping etc. Both of these containers need to write and read the data structures so it is important that consistency is maintained between them. To enable this, we have added some internal endpoints to both the shard manager as well as the load balancer that helps in exchanging data to maintain consistency. 

## Data Structures

### Load Balancer
The code implements a load balancer for a distributed database system. It utilizes various global data structures to manage server instances, shards, and other metadata efficiently. Here's an explanation of the key global data structures used in the code:

1. `sql_connection_pool`: This global variable represents a connection pool to the MySQL database server. It is used to manage and reuse database connections efficiently across multiple threads.

2. `server_id_to_hostname`: This dictionary maps server IDs to their respective hostnames. It keeps track of the mapping between server IDs and their corresponding hostnames for server management and communication purposes.

3. `server_id_to_shard`: This dictionary maps server IDs to the shards stored on each server. It maintains information about which shards are assigned to which servers, facilitating data distribution and load balancing.

4. `shard_data`: This list stores metadata about shards in the distributed database system. Each entry in the list represents information about a specific shard, such as its ID, size, and other properties.

5. `shard_to_server`: This dictionary maps shard IDs to the servers that store replicas of the shard's data. It is used in consistent hashing to determine the distribution of shards across servers.

6. `fast_server_assignment_map`: This dictionary maps shard IDs to lists of integers representing slots for fast server assignment. It is used in consistent hashing to quickly determine the assignment of shards to servers based on hash values.

### Shard Manager
The shard manager is responsible for tracking the health of each server. It spawns new server whenever any server crashes. It is also responsible for maintaining a primary server for each of the shard.

1. `PRIMARY_SERVERS`: This dictionary keeps the track of shard to primary server mapping. It is updated whenever any primary server is removed or crashes.


## Usage

1. Build the Load Balancer Docker image:
   ```bash
   make lb
   ```

2. Build the Shard Manager Docker image:
   ```bash
   make shardmanager
   ```

3. Build the Server Docker image:
   ```bash
   make server
   ```

4. Run the Docker container:
   ```bash
   make run
   ```

5. Stop and remove all the Docker containers:
   ```bash
   make stop
   ```

