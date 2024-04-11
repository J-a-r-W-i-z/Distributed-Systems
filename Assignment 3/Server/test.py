from flask import Flask, request, jsonify, g, Response
import itertools
import mysql.connector
import random
import requests
from time import sleep
import threading

app = Flask(__name__)


@app.route('/get', methods=['GET'])
def test():
    with open('test.wal', 'r') as f:
        return Response(f.read(), mimetype='text/plain')


@app.route('/set', methods=['POST'])
def test1():
    with open('test.wal', 'a') as f:
        f.write("hello world4\n")

    return "ok"


if __name__ == '__main__':
    app.run(debug=False, port=5000, host="0.0.0.0", threaded=True)
