# Laporan demo: tampilkan rencana Min-Min, hasil per task (rencana vs nyata), metrik,
# dan validasi otomatis dari satu folder hasil run di Kubernetes (kind).
# Pakai (dari root repo, tanpa perlu cluster menyala):
#   python real/demo_report.py data/GoCJ_Dataset_100.txt results_real/gocj100_minmin_run1
#   python real/demo_report.py data/GoCJ_Dataset_100.txt results_real/gocj100_minmin_run1 --rows 100
import argparse, csv, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("dataset")
ap.add_argument("result_dir")
ap.add_argument("--rows", type=int, default=20, help="jumlah baris tabel per-task yang ditampilkan")
ap.add_argument("--tol", type=float, default=20.0, help="batas atas deviasi makespan (persen)")
args = ap.parse_args()

os.environ.setdefault("CFG", "real/config.json")
os.environ["DATASET"] = args.dataset
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import controller as c   # memakai Min-Min yang sama persis dengan yang berjalan di cluster

N, M, MIPS, SCALE, LENGTH = c.N, c.M, c.MIPS, c.SCALE, c.LENGTH
task_vm, order, predicted = c.min_min(LENGTH, MIPS)

# ---- rencana: waktu mulai/selesai per task (detik skala simulasi) ----
ready = [0.0] * M
plan = {}
for i in order:
    j = task_vm[i]
    s = ready[j]; e = s + LENGTH[i] / MIPS[j]
    plan[i] = (s, e); ready[j] = e

rows = list(csv.DictReader(open(os.path.join(args.result_dir, "real_cloudlet_result.csv"), encoding="utf-8-sig")))
summ = {r["metrik"]: r["nilai"] for r in csv.DictReader(open(os.path.join(args.result_dir, "real_summary.csv"), encoding="utf-8-sig"))}
act = {int(r["cloudlet_id"]): dict(vm=int(r["vm_id"]), s=float(r["waktu_mulai"]), e=float(r["waktu_selesai"]),
                                   node=r["node"], ok=(r["status"] == "SUCCESS")) for r in rows}

print(f"=== TOPOLOGI ===")
print(f"1 datacenter | {c.HOSTS} host (node kind) | {c.PER} VM per host (pod worker) | total {M} VM")
for j in range(M):
    nodes = sorted({a["node"] for a in act.values() if a["vm"] == j})
    print(f"  vm-{j}: {MIPS[j]} MIPS | host {j // c.PER + 1} | node: {', '.join(nodes) if nodes else '-'}")

print(f"\n=== RENCANA MINMIN (skala waktu {SCALE}) | {N} task | {M} VM ===")
shown = order[:args.rows]
print("urut | task | MI      | VM   | MIPS | mulai(s) | selesai(s)   [detik skala simulasi]")
for k, i in enumerate(shown, 1):
    j = task_vm[i]
    print(f"{k:4d} | {i:4d} | {LENGTH[i]:7.0f} | vm-{j} | {MIPS[j]:4d} | {plan[i][0]:8.2f} | {plan[i][1]:9.2f}")
if N > len(shown):
    print(f"... ({N - len(shown)} task lainnya tidak ditampilkan, pakai --rows {N} untuk semua)")
print(f"Prediksi makespan: {predicted:.2f} detik (skala simulasi) = {predicted * SCALE:.2f} detik nyata")

print(f"\n=== HASIL PER TASK (detik nyata, rencana vs nyata) ===")
print("urut | task | VM rencana | VM nyata | mulai rencana/nyata | selesai rencana/nyata | status")
for k, i in enumerate(shown, 1):
    a = act[i]
    print(f"{k:4d} | {i:4d} | vm-{task_vm[i]:<7d} | vm-{a['vm']:<5d} | {plan[i][0] * SCALE:8.2f} / {a['s']:7.2f} | "
          f"{plan[i][1] * SCALE:9.2f} / {a['e']:7.2f}   | {'Succeeded' if a['ok'] else 'GAGAL'}")

makespan = float(summ["makespan_nyata_detik"]); mk_eq = float(summ["makespan_setara_simulasi_detik"])
ru = float(summ["resource_utilization_persen"]); wait = float(summ["average_waiting_time_detik"]); thr = float(summ["throughput_task_per_detik"])
dev = (mk_eq - predicted) / predicted * 100
busy = [sum(LENGTH[i] / MIPS[j] for i in range(N) if task_vm[i] == j) for j in range(M)]
ru_pred = sum(busy) / (M * predicted) * 100
wait_pred = sum(plan[i][0] for i in range(N)) / N

print(f"\n=== METRIK (prediksi simulasi vs nyata, skala simulasi) ===")
print(f"Makespan            : {predicted:10.2f} | {mk_eq:10.2f} detik   (deviasi {dev:+.1f}%)")
print(f"Resource Utilization: {ru_pred:10.2f} | {ru:10.2f} %")
print(f"Average Waiting     : {wait_pred:10.2f} | {wait / SCALE:10.2f} detik")
print(f"Throughput          : {N / predicted:10.4f} | {thr * SCALE:10.4f} task/detik")

# ---- validasi otomatis ----
checks = []
def chk(name, ok, info=""):
    checks.append(ok); print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {info}" if info else ""))

print(f"\n=== VALIDASI OTOMATIS ===")
n_ok = sum(a["ok"] for a in act.values())
chk("V1  semua task Succeeded", n_ok == N and len(act) == N, f"{n_ok} / {N}")
same_vm = sum(act[i]["vm"] == task_vm[i] for i in range(N))
chk("V2  tiap task berjalan di VM hasil rencana", same_vm == N, f"{same_vm} / {N}")
ord_ok = True
for j in range(M):
    got = [i for i in sorted(range(N), key=lambda x: act[x]["s"]) if act[i]["vm"] == j]
    want = [i for i in order if task_vm[i] == j]
    ord_ok &= (got == want)
chk("V3  urutan eksekusi per VM = urutan rencana", ord_ok)
overlap = 0
for j in range(M):
    q = sorted((act[i]["s"], act[i]["e"]) for i in range(N) if act[i]["vm"] == j)
    overlap += sum(q[k][0] < q[k - 1][1] - 0.05 for k in range(1, len(q)))
chk("V4  tidak ada task tumpang tindih di satu VM (space-shared)", overlap == 0, f"{overlap} tumpang tindih")
hosts = sorted({a["node"] for a in act.values()})
chk("V5  task tersebar di >= 2 host (node)", len(hosts) >= 2, ", ".join(hosts))
lb = sum(LENGTH) / sum(MIPS)
chk("V6  makespan >= batas bawah teoritis dan utilisasi <= 100%", mk_eq >= lb - 1e-6 and ru <= 100.0,
    f"makespan={mk_eq:.2f}  batas bawah={lb:.2f}  util={ru:.2f}%")
chk(f"V7  makespan nyata dekat prediksi (0% sampai +{args.tol:.0f}%)", -2.0 <= dev <= args.tol, f"deviasi={dev:+.1f}%")

print("\n" + ("SEMUA VALIDASI LULUS" if all(checks) else "ADA VALIDASI YANG GAGAL, cek baris FAIL di atas"))
sys.exit(0 if all(checks) else 1)
