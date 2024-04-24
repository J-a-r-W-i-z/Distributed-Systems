from flask import Flask, request, jsonify, g, Response
import itertools
import mysql.connector
import random
import requests
import os
from time import sleep
import threading

app = Flask(__name__)


@app.route('/read/<server_id>', methods=['GET'])
def read_server_data(server_id):
    server_id = int(server_id)


if __name__ == '__main__':
    app.run(debug=False, port=5000, host="0.0.0.0", threaded=True)
