from flask import Flask, request, jsonify, g
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

# Database configuration
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
MYSQL_DATABASE = 'stud_test'

# Pooling configuration
POOL_NAME = "my_pool"
POOL_SIZE = 5

connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name=POOL_NAME,
    pool_size=POOL_SIZE,
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE
)


@app.before_request
def before_request():
    if request.endpoint == 'heartbeat':
        return

    g.connection = connection_pool.get_connection()


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
            query = f"CREATE TABLE IF NOT EXISTS {shard} (\
                        {columns[0]} {map_dtype_to_sql(dtypes[0])} PRIMARY KEY,\
                        {columns[1]} {map_dtype_to_sql(dtypes[1])},\
                        {columns[2]} {map_dtype_to_sql(dtypes[2])}\
                    )"
            cursor.execute(query)
            g.connection.commit()

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "message": f"Failed to create table for {shards[0]} and {shards[1]}",
            "status": "error"
        }), 500
    finally:
        cursor.close()

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

    try:
        cursor = g.connection.cursor()

        response = {}
        for shard in shards:
            query = f"SELECT * FROM {shard}"
            cursor.execute(query)
            response[shard] = list_to_colmap(cursor)

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

        query = f"SELECT * FROM {shard} WHERE Stud_id BETWEEN {low_id} AND {high_id}"
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


@app.route('/write', methods=['POST'])
def write():
    pass  # TODO: Implement this method


@app.route('/update', methods=['PUT'])
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

    try:
        cursor = g.connection.cursor()

        cursor.execute(f"SELECT * FROM {shard} WHERE Stud_id = {stud_id}")
        if not cursor.fetchone():
            return jsonify({
                "message": f"Data entry for Stud_id:{stud_id} not found",
                "status": "error"
            }), 404

        update_columns = ', '.join(
            [f"{key} = '{value}'" for key, value in data.items()])
        query = f"UPDATE {shard} SET {update_columns} WHERE Stud_id = {stud_id}"
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


@app.route('/del', methods=['DELETE'])
def delete():
    payload = request.json

    if 'shard' not in payload or 'Stud_id' not in payload:
        return jsonify({
            "message": "Payload must contain 'shard' and 'Stud_id' keys",
            "status": "error"
        }), 400

    shard, stud_id = payload['shard'], payload['Stud_id']

    try:
        cursor = g.connection.cursor()

        cursor.execute(f"SELECT * FROM {shard} WHERE Stud_id = {stud_id}")
        if not cursor.fetchone():
            return jsonify({
                "message": f"Data entry for Stud_id:{stud_id} not found",
                "status": "error"
            }), 404

        query = f"DELETE FROM {shard} WHERE Stud_id = {stud_id}"
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
    app.run(debug=True, port=5000, threaded=True)
