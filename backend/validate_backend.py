import subprocess
import time
import urllib.request
import json
import os

print("Starting backend...")
env = os.environ.copy()
env['PYTHONPATH'] = '.'

proc = subprocess.Popen(["python", "main.py"], cwd=".", env=env)

time.sleep(3) # Wait for startup

try:
    print("Fetching /api/health...")
    req = urllib.request.Request("http://localhost:8000/api/health")
    with urllib.request.urlopen(req) as response:
        print("Status code:", response.getcode())
        print("Response:", json.loads(response.read().decode()))
except Exception as e:
    print("Error:", e)
finally:
    proc.terminate()
    print("Backend terminated.")
