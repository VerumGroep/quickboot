# Visualizer
This tool is designed to provide a live view of the memory state of the target device.

# Dependencies
Install the *requirements.txt* in the root of this project for all required dependencies.

# Starting

- Start JLinkGDBServer

```
$ JLinkGDBServer -port 4444 -device STM32F103RB -USB

```

- Start the visualizer server

```
$ ./server.py
 * Serving Flask app 'server'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:4445
 * Running on http://192.168.1.57:4445
Press CTRL+C to quit
127.0.0.1 - - [14/Feb/2026 16:28:59] "GET /snapshot HTTP/1.1" 200 -
127.0.0.1 - - [14/Feb/2026 16:29:00] "GET /snapshot HTTP/1.1" 200 -
```

- Start the visualizer client
Navigate to: https://quickboot.verumgroep.nl/

# IMPORTANT
- By default the visualizer refreshes the state every 5 seconds, this will halt the CPU.
- If you are halting the CPU while sending data over serial things **will break**
- Press the **run/stop button** in the top right corner to disable auto refresh
- Press **single** to refresh the memory state
