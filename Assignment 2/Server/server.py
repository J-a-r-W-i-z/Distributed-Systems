from flask import Flask, request, jsonify
import mysql.connector
import random

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
mysql_connection = MySQLConnection('localhost', 'user_name', 'password', 'database_name')

def get_connection():
    try:
        # Connection parameters
        connection = mysql.connector.connect(host='localhost',
                                             database='your_database_name',
                                             user='your_username',
                                             password='your_password')
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Connected to MySQL Server version {db_info}")
            cursor = connection.cursor()
            return connection, cursor
        
    except Exception as e:
        print(f"Error: {e}")

def close_connection(connection, cursor):
    try:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")
    except Exception as e:
        print(f"Error: {e}")



@app.route('/config', methods=['POST'])
def config():
    cursor = mysql_connection.connection.cursor()
    cursor.execute("SELECT * FROM your_table")
    data = cursor.fetchall()
    cursor.close()
#  This endpoint initializes the shard tables in the server database after the container
# is loaded. The shards are configured according to the request payload. An example request-response pair is shown below.
# 1 Payload Json= {
# 2 "schema":{"columns":["Stud_id","Stud_name","Stud_marks"],
# 3 "dtypes":["Number","String","String"]}
# 4 "shards":["sh1","sh2"]
# 5 }
# 2
# 6 Response Json ={
# 7 "message" : "Server0:sh1, Server0:sh2 configured",
# 8 "status" : "success"
# 9 },
# 10 Response Code = 200

    
    

@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    pass # TODO: Implement this method

@app.route('/copy', methods=['GET'])
def copy():
    pass # TODO: Implement this method

@app.route('/read', methods=['POST'])
def read():
    pass # TODO: Implement this method

@app.route('/write', methods=['POST'])
def write():
    pass # TODO: Implement this method

@app.route('/update', methods=['PUT'])
def update():
    pass # TODO: Implement this method

@app.route('/del', methods=['DELETE'])
def delete():
    pass # TODO: Implement this method

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)

