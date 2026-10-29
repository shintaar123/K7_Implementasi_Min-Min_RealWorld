import csv, json, os, sys, threading, time, urllib.request

CFG_PATH = os.environ.get("CFG", "/cfg/config.json")
OUT_DIR  = os.environ.get("RESULTS_DIR", "/results")
ENDPOINT = os.environ.get("VM_ENDPOINT", "http://vm-{j}:8080")   # {j} = id VM
ALGO     = os.environ.get("ALGO", "minmin")

CFG    = json.load(open(CFG_PATH))
SCALE  = CFG["time_scale"]
HOSTS, PER = CFG["hosts"], CFG["vms_per_host"]
M      = HOSTS * PER
MIPS   = [CFG["vm_types"][j % len(CFG["vm_types"])]["mips"] for j in range(M)]
LENGTH = [float(x) for x in open(os.environ["DATASET"]) if x.strip()]
N      = len(LENGTH)

def log(*a): print("#", *a, flush=True)          # baris berawalan '#' = log, bukan data
def url(j, path=""): return ENDPOINT.format(j=j) + path

# ---- Min-Min: port 1:1 dari MinMinScheduler.java (tie-break sama) ----
def min_min(length, mips):
    n, m = len(length), len(mips)
    ready, done = [0.0] * m, [False] * n
    task_vm, order = [0] * n, []
    for _ in range(n):
        best_ct, best_i, best_vm = float("inf"), -1, -1
        for i in range(n):
            if done[i]:
                continue
            vm, ct = 0, ready[0] + length[i] / mips[0]
            for j in range(1, m):
                c = ready[j] + length[i] / mips[j]
                if c < ct:                          # "<" murni -> seri: VM indeks terkecil
                    ct, vm = c, j
            if ct < best_ct:                        # seri: task indeks terkecil
                best_ct, best_i, best_vm = ct, i, vm
        ready[best_vm] = best_ct
        task_vm[best_i] = best_vm
        done[best_i] = True
        order.append(best_i)
    return task_vm, order, max(ready)

def round_robin(length, mips):                      # pembanding opsional
    return [i % len(mips) for i in range(len(length))], list(range(len(length))), None

if __name__ == "__main__":
    task_vm, order, predicted = (min_min if ALGO == "minmin" else round_robin)(LENGTH, MIPS)
    if predicted is not None:
        log(f"prediksi makespan (simulasi) = {predicted:.2f} s | skala {SCALE} -> {predicted*SCALE:.2f} s nyata")

    # ---- tunggu semua VM siap (retry, pod 'Running' belum tentu sudah listen) ----
    for j in range(M):
        for attempt in range(60):
            try:
                urllib.request.urlopen(url(j, "/"), timeout=5).read(); break
            except Exception:
                time.sleep(2)
        else:
            log(f"GAGAL: vm-{j} tidak merespons"); sys.exit(1)
    log(f"{M} VM siap")

    # ---- dispatch: 1 thread per VM, task berurutan sesuai order ----
    queues = [[i for i in order if task_vm[i] == j] for j in range(M)]
    res, errors = {}, []
    t0 = time.time()                                # semua task 'tiba' di t0

    def run_vm(j):
        try:
            for i in queues[j]:
                req = urllib.request.Request(
                    url(j, "/run"),
                    data=json.dumps({"task_id": i, "length_mi": LENGTH[i]}).encode(),
                    headers={"Content-Type": "application/json"})
                r = json.loads(urllib.request.urlopen(req, timeout=3600).read())
                res[i] = (r["start"] - t0, r["end"] - t0, r["node"])
        except Exception as e:
            errors.append(f"vm-{j}: {e}")

    ths = [threading.Thread(target=run_vm, args=(j,)) for j in range(M)]
    [t.start() for t in ths]; [t.join() for t in ths]
    if errors or len(res) != N:
        log("GAGAL:", errors, f"selesai {len(res)}/{N}"); sys.exit(1)

    # ---- metrik (definisi sama dengan MetricsCalculator di simulasi) ----
    makespan = max(v[1] for v in res.values())
    busy = [sum(res[i][1] - res[i][0] for i in queues[j]) for j in range(M)]
    ru = sum(busy) / (M * makespan) * 100
    avg_wait = sum(v[0] for v in res.values()) / N
    log(f"ALGO={ALGO} N={N}")
    log(f"makespan nyata = {makespan:.3f} s | setara skala simulasi = {makespan/SCALE:.2f} s")
    log(f"resource utilization = {ru:.2f} % | avg waiting = {avg_wait:.3f} s | throughput = {N/makespan:.4f} task/s")

    os.makedirs(OUT_DIR, exist_ok=True)
    pos = {t: k for k, t in enumerate(order)}
    with open(os.path.join(OUT_DIR, "real_cloudlet_result.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cloudlet_id", "panjang_MI", "urutan_dijadwalkan", "vm_id", "host_id",
                    "waktu_mulai", "waktu_selesai", "waiting_time", "node", "status"])
        for i in range(N):
            s, e, node = res[i]
            w.writerow([i, LENGTH[i], pos[i] + 1, task_vm[i], task_vm[i] // PER + 1,
                        f"{s:.4f}", f"{e:.4f}", f"{s:.4f}", node, "SUCCESS"])
    with open(os.path.join(OUT_DIR, "real_summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metrik", "nilai"])
        w.writerows([["algo", ALGO], ["n_task", N], ["makespan_nyata_detik", f"{makespan:.4f}"],
                     ["makespan_setara_simulasi_detik", f"{makespan/SCALE:.4f}"],
                     ["makespan_prediksi_simulasi_detik", predicted if predicted else ""],
                     ["resource_utilization_persen", f"{ru:.4f}"],
                     ["average_waiting_time_detik", f"{avg_wait:.4f}"],
                     ["throughput_task_per_detik", f"{N/makespan:.4f}"]])
    log("selesai")
