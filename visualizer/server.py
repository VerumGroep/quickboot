#!/usr/bin/env python3

import threading
import json
import sys

from enum import Enum
from pathlib import Path
from time import time_ns

from pygdbmi.gdbcontroller import GdbController
from flask import Flask
from flask_cors import CORS

CURRENT_DIRECTORY = Path('.')
FIRMWARE_DIRECTORY = CURRENT_DIRECTORY / Path('../bin/')
FIRMWARE_IMAGE = FIRMWARE_DIRECTORY / Path('firmware.elf')
VISUALIZE_SCRIPT = CURRENT_DIRECTORY / Path('visualize.py')

class DebuggerState(Enum):
    STOPPED = 0
    RUNNING = 1


app = Flask(__name__)
gdbmi = GdbController(['gdb-multiarch', '--interpreter=mi2', FIRMWARE_IMAGE.resolve().as_posix()])

"""
We need to keep track of the state because this script can be called asynchronous 
"""
_lock_state =  threading.Lock()
state = DebuggerState.STOPPED

CORS(app)

# // --------------------------------------------------------

def halt(timeout: int = 2000):
    global state
    if state is DebuggerState.STOPPED:
        return

    resp = gdbmi.write("-exec-interrupt")    
    while time_ns() < time_ns() + (timeout * 1000000):        
        for m in resp:
            if m["type"] == "notify" and m["message"] == "stopped":
                state = DebuggerState.STOPPED
                return
            
        resp = gdbmi.get_gdb_response(timeout_sec=2)
    
    raise TimeoutError(f"Target did not halt within {timeout} ms")

def run(timeout: int = 2000):    
    global state
    if state is DebuggerState.RUNNING:
        return

    resp = gdbmi.write("-exec-continue")    
    while time_ns() < time_ns() + (timeout * 1000000):        
        for m in resp:
            if m["type"] == "result" and m["message"] == "running":
                state = DebuggerState.RUNNING
                return
            
        resp = gdbmi.get_gdb_response(timeout_sec=2)
    
    raise TimeoutError(f"Target did not continue within {timeout} ms")

@app.route('/snapshot')
def get_snapshot():
    global _lock_state
    try:
        with _lock_state:
            halt()
            resp = gdbmi.write(f"source {VISUALIZE_SCRIPT.as_posix()}")
            json = {'error': 'No response from target'}

            for m in resp:
                if m["stream"] == "stdout" and m["type"] == "console":
                    json = m["payload"]

            run()
    except TimeoutError:
        return {'error': 'Timeout'}      

    return json

if __name__ == "__main__":     
    gdbmi.write("set pagination off")
    gdbmi.write("set target-async on")
    gdbmi.write("set non-stop off")   
    gdbmi.write("target remote :4444") 
    run()

    app.run(host='0.0.0.0', port=4445)