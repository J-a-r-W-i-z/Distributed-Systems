from flask import Flask, request, jsonify, current_app
import mysql.connector
import random
import itertools


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
# create a mysql connection pool
# MYSQL_HOST = 'localhost'
# MYSQL_USER = 'root'
# MYSQL_PASSWORD = 'password'
# MYSQL_DATABASE = 'test'
# connection_pool = mysql.connector.pooling.MySQLConnectionPool(
#     pool_name="my_pool",
#     pool_size=5,
#     host=MYSQL_HOST,
#     user=MYSQL_USER,
#     password=MYSQL_PASSWORD,
#     database=MYSQL_DATABASE
# )


@app.before_request
def before_request():
    try:
        connection = mysql.connector.connect(host='localhost',
                                             database='stud_test',
                                             user='root',
                                             password='password')
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Connected to MySQL Server version {db_info}")
            cursor = connection.cursor()
            current_app.config['connection'] = connection
            current_app.config['cursor'] = cursor
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        raise ConnectionError("Failed to connect to MySQL server")


@app.teardown_request
def teardown_request(exception):
    connection = current_app.config.get('connection')
    cursor = current_app.config.get('cursor')
    if connection and connection.is_connected():
        cursor.close()
        connection.close()
        print("MySQL connection is closed")


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
            "message": "columns and dtypes must be provided and have the same length",
            "status": "error"
        }), 400

    try:
        cursor = current_app.config['cursor']
        connection = current_app.config['connection']
        for shard in shards:
            query = f"CREATE TABLE IF NOT EXISTS {shard} (\
                        {columns[0]} {map_dtype_to_sql(dtypes[0])} PRIMARY KEY,\
                        {columns[1]} {map_dtype_to_sql(dtypes[1])},\
                        {columns[2]} {map_dtype_to_sql(dtypes[2])}\
                    )"
            cursor.execute(query)
            connection.commit()

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "message": f"Failed to create table for {shards[0]} and {shards[1]}",
            "status": "error"
        }), 500

    return jsonify({
        "message": f"Server0:{shards[0]}, Server0:{shards[1]} configured",
        "status": "success"
    }), 200


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

    response = {}
    try:
        cursor = current_app.config['cursor']

        for shard in shards:
            query = f"SELECT * FROM {shard}"
            cursor.execute(query)
            response[shard] = list_to_colmap(cursor)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "message": f"Failed to query data",
            "status": "error"
        }), 500

    response['status'] = 'success'
    return jsonify(response), 200


@app.route('/read', methods=['POST'])
def read():
    pass  # TODO: Implement this method


@app.route('/write', methods=['POST'])
def write():
    pass  # TODO: Implement this method


@app.route('/update', methods=['PUT'])
def update():
    pass  # TODO: Implement this method


@app.route('/del', methods=['DELETE'])
def delete():
    pass  # TODO: Implement this method


def list_to_colmap(cursor):
    desc = cursor.description
    column_names = [col[0] for col in desc]
    return [{column_names[i]: row[i] for i in range(len(row))} for row in cursor.fetchall()]


def map_dtype_to_sql(dtype):
    if dtype.lower() == 'number':
        return 'INT'
    elif dtype.lower() == 'string':
        return 'VARCHAR(50)'
    else:
        raise ValueError(f"Unsupported data type: {dtype}")


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
