import os
import sys
import time
import socket
import subprocess
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 65)
print("  CYBERBULLYING DETECTION IN HINGLISH - MASTER LAUNCHER")
print("=" * 65)

# 1. Start Web & API Server
print("[1/3] Starting SafeChat Web Portal & REST Service (Port 5000)...")
web_process = subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "web_app.py")])

# Wait for port 5000 to become responsive
for _ in range(15):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 5000))
        s.close()
        break
    except Exception:
        time.sleep(0.5)

print("[2/3] Opening SafeChat Web UI in your default browser...")
try:
    webbrowser.open("http://127.0.0.1:5000")
except Exception as e:
    print(f"Could not open browser automatically: {e}")

# 2. Launch Desktop GUI Client
print("[3/3] Launching Desktop Tkinter SafeChat GUI...")
gui_script = os.path.join(BASE_DIR, "Safe_Chat", "client_GUI.py")
gui_process = subprocess.Popen([sys.executable, gui_script])

print("\n" + "=" * 65)
print("  PROJECT IS NOW RUNNING SUCCESSFULLY!")
print("  * Web Portal: http://127.0.0.1:5000")
print("  * Socket Server: 127.0.0.1:12345")
print("  * Desktop Tkinter GUI: Active on screen")
print("=" * 65)
print("Press Ctrl+C in this terminal anytime to stop all services.\n")

try:
    gui_process.wait()
    web_process.wait()
except KeyboardInterrupt:
    print("\nStopping services...")
    gui_process.terminate()
    web_process.terminate()
    print("All services stopped.")
