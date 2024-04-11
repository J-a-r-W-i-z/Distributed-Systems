import bisect
from collections import deque
import queue
from flask import Flask, request, jsonify, Response
import mysql.connector
import os
import subprocess
import random
import copy
import requests
from time import sleep
import threading
import requests


LIVENESS_SLEEP_TIME = 5
app = Flask(__name__)

def liveness_checker():
    while True:
        

        sleep(LIVENESS_SLEEP_TIME)
        