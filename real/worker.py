import json, os, time
from http.server import BaseHTTPRequestHandler, HTTPServer

VM_ID      = int(os.environ["VM_ID"])
VM_MIPS    = float(os.environ["VM_MIPS"])
TIME_SCALE = float(os.environ.get("TIME_SCALE", "0.05"))
OPS_PER_MI = float(os.environ.get("OPS_PER_MI", "100"))
MODE       = os.environ.get("MODE", "cpu")      # cpu = asli, sleep = hanya untuk debug alur
NODE       = os.environ.get("NODE_NAME", "?")
PORT       = int(os.environ.get("PORT", "8080"))

def burn(n):                                    # HARUS sama dengan loop di calibrate.py
    x = 0.0
    for i in range(n):
        x += i * 0.5
    return x

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        self._send({"vm_id": VM_ID, "node": NODE, "mips": VM_MIPS})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        length = float(body["length_mi"])
        t_start = time.time()
        if MODE == "sleep":
            time.sleep(TIME_SCALE * length / VM_MIPS)
        else:
            burn(int(length * OPS_PER_MI))
        t_end = time.time()
        self._send({"task_id": body["task_id"], "vm_id": VM_ID, "node": NODE,
                    "start": t_start, "end": t_end})

# HTTPServer biasa (satu thread) = satu task per waktu, FIFO, non-preemptive
HTTPServer(("", PORT), H).serve_forever()
