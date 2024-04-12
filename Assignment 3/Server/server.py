from flask import Flask, request, jsonify, g, Response
import itertools
import mysql.connector
import random
import requests
import os
from time import sleep
import threading

primary_map = {}
primary_map_lock = threading.Lock()


class MySQLConnection:
    _instance = None

    def __new__(cls, host, user, password, database):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
        return cls._instance

    @property
    def connection(self):
        return self._instance._connection


app = Flask(__name__)

sql_connection_pool = None
MAX_RETRY = 1000


def connect_to_sql_server(max_pool_size=30, host='localhost', user='root', password='password', database='mydb'):
    global sql_connection_pool
    flag = True
    tries = 0
    while True:
        if tries > MAX_RETRY:
            print(
                "Max retry limit reached.\n Couldn't connect to MySql server\n Exiting...")
            exit(1)
        try:
            if flag:
                print("Creating MySQL connection pool...")
                flag = False
            else:
                print("Retrying to connect to mysql server...")
                sleep(3)
            if sql_connection_pool is None:
                sql_connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                    pool_name="my_pool",
                    pool_size=max_pool_size,
                    host=host,
                    user=user,
                    password=password,
                    database=database
                )
                return
        except Exception as e:
            tries += 1
            print(f"Error occursed while connecting to sql server: {e}")


@app.before_request
def before_request():
    if request.endpoint == 'heartbeat':
        return

    g.connection = sql_connection_pool.get_connection()


@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'connection'):
        g.connection.close()


@app.route('/config', methods=['POST'])
def config():
    payload = request.json

    if 'shards' not in payload or 'schema' not in payload:
        return jsonify({
            "message": "Payload must contain 'shards' and 'schema' keys",
            "status": "error"
        }), 400

    schema, shards = payload['schema'], payload['shards']
    columns, dtypes = schema['columns'], schema['dtypes']

    if not columns or not dtypes or len(columns) != len(dtypes):
        return jsonify({
            "message": "columns and dtypes must be provided in schema and have the same length",
            "status": "error"
        }), 400

    try:
        cursor = g.connection.cursor()
        for shard in shards:
            query = f"CREATE TABLE IF NOT EXISTS `{shard}` (\
                        {columns[0]} {map_dtype_to_sql(dtypes[0])} PRIMARY KEY,\
                        {columns[1]} {map_dtype_to_sql(dtypes[1])},\
                        {columns[2]} {map_dtype_to_sql(dtypes[2])}\
                    )"
            print(query)
            cursor.execute(query)
            g.connection.commit()

        return jsonify({
            "message": f"Server0:{shards[0]}, Server0:{shards[1]} configured",
            "status": "success"
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "message": f"Failed to create table for {shards[0]} and {shards[1]}",
            "status": "error"
        }), 500
    finally:
        cursor.close()


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    return '', 200


@app.route('/copy', methods=['GET'])
def copy():
    paylod = request.json

    if 'shards' not in paylod:
        return jsonify({
            "message": "Payload must contain 'shards' key",
            "status": "error"
        }), 400

    shards = paylod['shards']

    try:
        cursor = g.connection.cursor()

        response = {}
        for shard in shards:
            query = f"SELECT * FROM `{shard}`"
            cursor.execute(query)
            response[str(shard)] = list_to_colmap(cursor)

        response['status'] = 'success'
        return jsonify(response), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "message": f"Failed to query data",
            "status": "error"
        }), 500
    finally:
        cursor.close()


@app.route('/read', methods=['POST'])
def read():
    payload = request.json

    if 'shard' not in payload or 'Stud_id' not in payload:
        return jsonify({
            "message": "Payload must contain 'shard' and 'Stud_id' keys",
            "status": "error"
        }), 400

    shard, stud_id_range = payload['shard'], payload['Stud_id']

    if 'low' not in stud_id_range or 'high' not in stud_id_range:
        return jsonify({
            "message": "Stud_id must contain 'low' and 'high' keys",
            "status": "error"
        }), 400

    low_id, high_id = stud_id_range['low'], stud_id_range['high']

    try:
        cursor = g.connection.cursor()

        query = f"SELECT * FROM `{shard}` WHERE Stud_id BETWEEN {low_id} AND {high_id}"
        cursor.execute(query)
        response = {"data": list_to_colmap(cursor), "status": "success"}
        return jsonify(response), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "message": f"Failed to query data",
            "status": "error"
        }), 500
    finally:
        cursor.close()


@app.route('/write', methods=['POST'])  # TODO: Update according to assign 3
def write():
    payload = request.json

    if 'shard' not in payload or 'data' not in payload:
        return jsonify({
            "message": "Payload must contain 'shard', 'curr_idx' and 'data' keys",
            "status": "error"
        }), 400

    shard, data = payload['shard'],  payload['data']

    with open(f"{shard}.wal", "a") as f:
        f.write(f"W: {data}\n")

    if not is_primary(shard):
        return write_to_db(shard, data)

    if not response_status(shard, "write", payload):
        return jsonify({
            "message": "Failed to write data entries",
            "status": "error"
        }), 500

    return write_to_db(shard, data)


def write_to_db(shard, data):
    try:
        cursor = g.connection.cursor()

        cursor.execute(f"SELECT Stud_id FROM `{shard}`")
        existing_ids = {row[0] for row in cursor.fetchall()}

        filtered_data = [
            entry for entry in data if entry['Stud_id'] not in existing_ids]

        for entry in filtered_data:
            columns = ', '.join(entry.keys())
            values = ', '.join(f"'{value}'" for value in entry.values())
            query = f"INSERT INTO `{shard}` ({columns}) VALUES ({values})"
            cursor.execute(query)

        g.connection.commit()

        return jsonify({
            "message": "Data entries added",
            "status": "success"
        }), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "message": f"Failed to add data entries",
            "status": "error"
        }), 500
    finally:
        cursor.close()


@app.route('/update', methods=['PUT'])  # TODO: Update according to assign 3
def update():
    payload = request.json

    if 'shard' not in payload or 'Stud_id' not in payload or 'data' not in payload:
        return jsonify({
            "message": "Payload must contain 'shard', 'Stud_id' and 'data' keys",
            "status": "error"
        }), 400

    shard, stud_id, data = payload['shard'], payload['Stud_id'], payload['data']

    if 'Stud_id' not in data or int(data['Stud_id']) != stud_id:
        return jsonify({
            "message": "Stud_id must be provided in data and match Stud_id in payload",
            "status": "error"
        }), 400

    with open(f"{shard}.wal", "a") as f:
        f.write(f"U: {data}\n")

    if not is_primary(shard):
        return update_in_db(shard, data)

    if not response_status(shard, "update", payload):
        return jsonify({
            "message": "Failed to update data entry",
            "status": "error"
        }), 500

    return update_in_db(shard, data)


def update_in_db(shard, data):
    stud_id = data['Stud_id']
    try:
        cursor = g.connection.cursor()

        cursor.execute(f"SELECT * FROM `{shard}` WHERE Stud_id = {stud_id}")
        if not cursor.fetchone():
            return jsonify({
                "message": f"Data entry for Stud_id:{stud_id} not found",
                "status": "error"
            }), 404

        update_columns = ', '.join(
            [f"{key} = '{value}'" for key, value in data.items()])
        query = f"UPDATE `{shard}` SET {update_columns} WHERE Stud_id = {stud_id}"
        cursor.execute(query)
        g.connection.commit()

        return jsonify({
            "message": f"Data entry for Stud_id:{stud_id} updated",
            "status": "success"
        }), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "message": f"Failed to update data entry for Stud_id:{stud_id}",
            "status": "error"
        }), 500
    finally:
        cursor.close()


@app.route('/del', methods=['DELETE'])  # TODO: Update according to assign 3
def delete():
    payload = request.json

    if 'shard' not in payload or 'Stud_id' not in payload:
        return jsonify({
            "message": "Payload must contain 'shard' and 'Stud_id' keys",
            "status": "error"
        }), 400

    shard, stud_id = payload['shard'], payload['Stud_id']

    with open(f"{shard}.wal", "a") as f:
        f.write(f"D: {stud_id}\n")

    if not is_primary(shard):
        return delete_from_db(shard, stud_id)

    if not response_status(shard, "del", payload):
        return jsonify({
            "message": "Failed to remove data entry",
            "status": "error"
        }), 500

    return delete_from_db(shard, stud_id)


def delete_from_db(shard, stud_id):
    try:
        cursor = g.connection.cursor()

        cursor.execute(f"SELECT * FROM `{shard}` WHERE Stud_id = {stud_id}")
        if not cursor.fetchone():
            return jsonify({
                "message": f"Data entry for Stud_id:{stud_id} not found",
                "status": "error"
            }), 404

        query = f"DELETE FROM `{shard}` WHERE Stud_id = {stud_id}"
        cursor.execute(query)
        g.connection.commit()

        return jsonify({
            "message": f"Data entry for Stud_id:{stud_id} removed",
            "status": "success"
        }), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "message": f"Failed to remove data entry for Stud_id:{stud_id}",
            "status": "error"
        }), 500
    finally:
        cursor.close()


@app.route('/wal', methods=['POST'])
def wal():
    print("starting wal")
    payload = request.json

    if 'shard' not in payload:
        return jsonify({
            "message": "Payload must contain 'shard' key",
            "status": "error"
        }), 400

    shard = payload['shard']

    try:
        # current path
        path = os.getcwd()
        print("path: ", path)
        os.system("ls")

        # print whether there is permission to create a file
        print("Permission: ", os.access(path, os.W_OK))

        # create a new directory called wal if not exists in the current path
        if not os.path.exists(f"{path}/wal"):
            os.makedirs(f"{path}/wal")

        try:
            print("file contents")
            with open(f"{path}/wal/{shard}.wal", "a") as f:
                print(f.read())
                return Response(f.read(), mimetype='text/plain')
        except Exception as e:
            print("Exception", e)

    except OSError as e:
        print(f"Error: {e}")
        return jsonify({
            "message": f"Failed to read WAL file for shard {shard}",
            "status": "error"
        }), 500
    # except FileNotFoundError:
    #     return jsonify({
    #         "message": f"WAL file for shard {shard} not found",
    #         "status": "error"
    #     }), 404


@app.route('/make_primary', methods=['POST'])
def make_primary():
    # TODO: Implement this endpoint that makes this server primary for particular shard (Just add to primary_map)
    # pass
    # payload form-
    # {
    #   "shard": "shard1",
    #   "secondary": ["server1_hostname", "server2_hostname"]
    # }
    payload = request.json

    if 'shard' not in payload or 'secondary' not in payload:
        return jsonify({
            "message": "Payload must contain 'shard' and 'secondary' keys",
            "status": "error"
        }), 400

    shard, secondary = payload['shard'], payload['secondary']

    if not isinstance(secondary, list):
        return jsonify({
            "message": "Secondary must be a list of hostnames",
            "status": "error"
        }), 400

    with primary_map_lock:
        primary_map[shard] = secondary
    return jsonify({
        "status": "success",
    }), 200


def is_primary(shard):
    with primary_map_lock:
        return shard in primary_map


def response_status(shard, endpoint, payload):
    with primary_map_lock:
        secondary_servers = primary_map[shard]

    responses = []
    for hostname in secondary_servers:
        response = requests.delete(
            f"http://{hostname}:5000/{endpoint}", json=payload)
        responses.append(response)

    return all(response.status_code == 200 for response in responses)


def list_to_colmap(cursor):
    return [dict(zip(cursor.column_names, row))
            for row in cursor.fetchall()]


def map_dtype_to_sql(dtype):
    if dtype.lower() == 'number':
        return 'INT'
    elif dtype.lower() == 'string':
        return 'VARCHAR(50)'
    else:
        raise ValueError(f"Unsupported data type: {dtype}")


if __name__ == '__main__':
    print("Running server...")
    connect_to_sql_server()
    app.run(debug=False, port=5000, host="0.0.0.0", threaded=True)
