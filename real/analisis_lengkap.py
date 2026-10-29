"""Analisis lengkap hasil Min-Min di Kubernetes (simulasi vs nyata).

Jalankan dari root repo (soka-realworld):
    python real/analisis_lengkap.py
    python real/analisis_lengkap.py results_real gocj300     # folder, dataset untuk grafik detail

Output (folder <hasil>/grafik/ dan <hasil>/):
  ringkasan_deviasi.csv, ringkasan_deviasi.md
  grafik_1_makespan_sim_vs_nyata.png   grafik_2_deviasi.png
  grafik_3_utilization_throughput.png  grafik_4_beban_vm.png
  grafik_5_urutan_vs_panjang.png       grafik_6_waiting_time.png
  grafik_7_gantt_vm.png                grafik_8_per_run.png
"""
import csv, glob, os, re, sys, statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------- format angka Indonesia: titik ribuan, koma desimal ----------
from matplotlib.ticker import FuncFormatter, ScalarFormatter
def idf(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
def _tick(v, _):
    return idf(v, 0 if abs(v - round(v)) < 1e-9 else 1)
def localize(fig):
    """Ubah label sumbu numerik jadi format Indonesia (sumbu kategori/teks tidak disentuh)."""
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            if isinstance(axis.get_major_formatter(), ScalarFormatter):
                axis.set_major_formatter(FuncFormatter(_tick))


ROOT = sys.argv[1] if len(sys.argv) > 1 else "results_real"
DETAIL = sys.argv[2] if len(sys.argv) > 2 else "gocj300"   # dataset untuk grafik 4-7
OUT = os.path.join(ROOT, "grafik")
os.makedirs(OUT, exist_ok=True)
LABEL = {f"gocj{n}": f"GoCJ-{n}" for n in range(100, 1001, 100)}
LABEL.update({f"syn{n}": f"Synthetic-{n}" for n in range(1000, 10001, 1000)})
ALGO = "minmin"
LIMIT = 15.0   # ambang deviasi di plan (%)

def num(x):
    try: return float(str(x).replace(",", "."))
    except Exception: return None

def read_summary(path):
    d = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        v = num(r["nilai"]); d[r["metrik"]] = v if v is not None else r["nilai"]
    return d

def ms(xs):
    return st.mean(xs), (st.stdev(xs) if len(xs) > 1 else 0.0)

# ---------- baca semua run ----------
runs = {}   # dataset -> list of dict
for f in sorted(glob.glob(os.path.join(ROOT, "*_" + ALGO + "_run*", "real_summary.csv"))):
    name = os.path.basename(os.path.dirname(f))
    m = re.match(r"(.+?)_" + ALGO + r"_run(\d+)$", name)
    if not m: continue
    s = read_summary(f)
    pred, real = s["makespan_prediksi_simulasi_detik"], s["makespan_setara_simulasi_detik"]
    runs.setdefault(m.group(1), []).append({
        "run": int(m.group(2)), "dir": os.path.dirname(f), "pred": pred, "real": real,
        "real_s": s["makespan_nyata_detik"], "dev": abs(real - pred) / pred * 100,
        "ru": s["resource_utilization_persen"], "wait": s["average_waiting_time_detik"],
        "thr": s["throughput_task_per_detik"], "n": int(s["n_task"])})
keys = [k for k in LABEL if k in runs] + [k for k in runs if k not in LABEL]
if not keys:
    sys.exit("Tidak ada run ditemukan di " + ROOT)

# ---------- tabel ringkasan ----------
rows = []
for k in keys:
    g = runs[k]; pred = g[0]["pred"]
    rm, rs = ms([x["real"] for x in g]); dm, ds = ms([x["dev"] for x in g])
    um, us = ms([x["ru"] for x in g]); wm, ws = ms([x["wait"] for x in g])
    tm, ts = ms([x["thr"] for x in g])
    rows.append(dict(key=k, label=LABEL.get(k, k), n=g[0]["n"], runs=len(g), pred=pred,
                     rm=rm, rs=rs, dm=dm, ds=ds, um=um, us=us, wm=wm, ws=ws, tm=tm, ts=ts))
with open(os.path.join(ROOT, "ringkasan_deviasi.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["dataset", "n_task", "n_run", "prediksi_s", "nyata_mean_s", "nyata_sd_s",
                "deviasi_mean_%", "deviasi_sd_%", "util_mean_%", "util_sd_%",
                "waiting_mean_s", "waiting_sd_s", "throughput_mean", "throughput_sd"])
    for r in rows:
        w.writerow([r["label"], r["n"], r["runs"], r["pred"], round(r["rm"], 2), round(r["rs"], 2),
                    round(r["dm"], 2), round(r["ds"], 2), round(r["um"], 2), round(r["us"], 2),
                    round(r["wm"], 2), round(r["ws"], 2), round(r["tm"], 4), round(r["ts"], 4)])
with open(os.path.join(ROOT, "ringkasan_deviasi.md"), "w", encoding="utf-8") as fh:
    fh.write("| Dataset | Task | Ulangan | Prediksi sim (s) | Nyata setara (s) | Deviasi (%) | Utilization (%) | Avg waiting (s) | Throughput (task/s) |\n")
    fh.write("|---|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        fh.write(f"| {r['label']} | {r['n']} | {r['runs']} | {r['pred']:.2f} | {r['rm']:.1f} ± {r['rs']:.1f} | "
                 f"{r['dm']:.1f} ± {r['ds']:.1f} | {r['um']:.1f} ± {r['us']:.1f} | "
                 f"{r['wm']:.1f} ± {r['ws']:.1f} | {r['tm']:.3f} ± {r['ts']:.3f} |\n")
print(open(os.path.join(ROOT, "ringkasan_deviasi.md"), encoding="utf-8").read())

labels = [r["label"] for r in rows]; X = list(range(len(rows)))
def save(name):
    localize(plt.gcf()); plt.tight_layout(); plt.savefig(os.path.join(OUT, name), dpi=200); plt.close()

# G1 makespan sim vs nyata
plt.figure(figsize=(9, 5))
plt.bar([i - .2 for i in X], [r["pred"] for r in rows], .4, label="Simulasi (prediksi)", color="#4C78A8")
plt.bar([i + .2 for i in X], [r["rm"] for r in rows], .4, yerr=[r["rs"] for r in rows],
        capsize=4, label="Nyata Kubernetes (rata-rata ± SD)", color="#F58518")
plt.xticks(X, labels); plt.ylabel("Makespan (detik, skala simulasi)")
plt.title("Makespan Min-Min: simulasi vs Kubernetes"); plt.legend(); save("grafik_1_makespan_sim_vs_nyata.png")

# G2 deviasi
plt.figure(figsize=(9, 5))
b = plt.bar(X, [r["dm"] for r in rows], .5, yerr=[r["ds"] for r in rows], capsize=4, color="#54A24B")
for i, r in enumerate(rows):
    plt.text(i, r["dm"] + r["ds"] + .3, idf(r['dm'], 1) + "%", ha="center")
plt.axhline(LIMIT, color="red", ls="--", label=f"Ambang {LIMIT:.0f}% (plan)")
plt.xticks(X, labels); plt.ylabel("Deviasi makespan (%)")
plt.title("Deviasi nyata vs prediksi simulasi"); plt.legend(); save("grafik_2_deviasi.png")

# G3 utilization & throughput
fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
ax[0].bar(X, [r["um"] for r in rows], .5, yerr=[r["us"] for r in rows], capsize=4, color="#B279A2")
ax[0].set_ylim(0, 105); ax[0].set_xticks(X); ax[0].set_xticklabels(labels, rotation=15)
ax[0].set_ylabel("Resource utilization (%)"); ax[0].set_title("Resource utilization")
ax[1].bar(X, [r["tm"] for r in rows], .5, yerr=[r["ts"] for r in rows], capsize=4, color="#E45756")
ax[1].set_xticks(X); ax[1].set_xticklabels(labels, rotation=15)
ax[1].set_ylabel("Throughput (task/s nyata)"); ax[1].set_title("Throughput")
save("grafik_3_utilization_throughput.png")

# G8 per run
plt.figure(figsize=(9, 5))
for k in keys:
    g = sorted(runs[k], key=lambda x: x["run"])
    plt.plot([x["run"] for x in g], [x["dev"] for x in g], marker="o", label=LABEL.get(k, k))
plt.axhline(LIMIT, color="red", ls="--"); plt.xticks([1, 2, 3])
plt.xlabel("Ulangan ke-"); plt.ylabel("Deviasi (%)"); plt.title("Deviasi per ulangan"); plt.legend()
save("grafik_8_per_run.png")

# ---------- grafik detail (dari real_cloudlet_result.csv) ----------
def pick(cols, *words, avoid=()):
    for c in cols:
        lc = c.lower()
        if any(w in lc for w in words) and not any(a in lc for a in avoid):
            return c
    return None

def load_cloudlets(g):
    p = os.path.join(g["dir"], "real_cloudlet_result.csv")
    rows_ = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    cols = list(rows_[0].keys())
    c = {"vm": pick(cols, "vm_id", "vmid", "vm", "worker"),
         "len": pick(cols, "length", "panjang", "_mi", "mi"),
         "start": pick(cols, "start", "mulai"),
         "fin": pick(cols, "finish", "selesai", "end", "akhir"),
         "ord": pick(cols, "urutan", "order"),
         "wait": pick(cols, "wait", "tunggu")}
    return rows_, cols, c

if DETAIL not in runs:
    print(f"Dataset detail '{DETAIL}' tidak ada; grafik 4-7 dilewati."); sys.exit(0)
g = sorted(runs[DETAIL], key=lambda x: x["run"])[0]
data, cols, c = load_cloudlets(g)
print("Kolom real_cloudlet_result.csv:", cols); print("Terdeteksi:", c)
need = ["vm", "start", "fin"]
if any(c[k] is None for k in need):
    sys.exit("Kolom vm/start/finish tidak terdeteksi. Tempel baris 'Kolom ...' di atas ke Claude.")

T = [dict(vm=int(num(r[c["vm"]])) if num(r[c["vm"]]) is not None else int(re.sub(r"\D", "", r[c["vm"]])),
          s=num(r[c["start"]]), f=num(r[c["fin"]]),
          L=num(r[c["len"]]) if c["len"] else None,
          o=num(r[c["ord"]]) if c["ord"] else None,
          w=num(r[c["wait"]]) if c["wait"] else None) for r in data]
# samakan satuan waktu ke "setara simulasi"
mx = max(t["f"] for t in T)
if abs(mx - g["real_s"]) < abs(mx - g["real"]):          # CSV masih detik nyata
    fac = g["real"] / g["real_s"]
    for t in T:
        t["s"] *= fac; t["f"] *= fac
        if t["w"] is not None: t["w"] *= fac
mk = max(t["f"] for t in T)
nvm = max(t["vm"] for t in T) + 1
ttl = f"{LABEL.get(DETAIL, DETAIL)} (run {g['run']})"
vmcol = ["#4C78A8", "#72B7B2", "#54A24B", "#F58518", "#E45756", "#B279A2"]
vmtype = ["S", "M", "L"]

# G4 beban per VM
busy = [sum(t["f"] - t["s"] for t in T if t["vm"] == j) for j in range(nvm)]
ntask = [sum(1 for t in T if t["vm"] == j) for j in range(nvm)]
fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
ax[0].bar(range(nvm), [b / mk * 100 for b in busy], color=vmcol[:nvm])
for j in range(nvm): ax[0].text(j, busy[j] / mk * 100 + 1, idf(busy[j] / mk * 100, 1) + "%", ha="center")
ax[0].set_ylim(0, 110); ax[0].set_xticks(range(nvm))
ax[0].set_xticklabels([f"vm-{j}\n{vmtype[j % 3]}" for j in range(nvm)])
ax[0].set_ylabel("Utilisasi VM (%)"); ax[0].set_title("Utilisasi per VM")
ax[1].bar(range(nvm), ntask, color=vmcol[:nvm])
for j in range(nvm): ax[1].text(j, ntask[j] + .5, str(ntask[j]), ha="center")
ax[1].set_xticks(range(nvm)); ax[1].set_xticklabels([f"vm-{j}" for j in range(nvm)])
ax[1].set_ylabel("Jumlah task"); ax[1].set_title("Task per VM")
fig.suptitle("Beban per VM — " + ttl); save("grafik_4_beban_vm_"+DETAIL+".png")

# G5 urutan vs panjang
if c["len"]:
    ts_ = sorted(T, key=lambda t: (t["o"] if t["o"] is not None else t["s"]))
    plt.figure(figsize=(9, 5))
    plt.scatter(range(1, len(ts_) + 1), [t["L"] for t in ts_], s=10, c=[vmcol[t["vm"] % 6] for t in ts_])
    plt.xlabel("Urutan dijadwalkan" if c["ord"] else "Urutan (berdasar waktu mulai)")
    plt.ylabel("Panjang task (MI)"); plt.title("Urutan dijadwalkan vs panjang task — " + ttl)
    save("grafik_5_urutan_vs_panjang_"+DETAIL+".png")

# G6 waiting time
W = [t["w"] if t["w"] is not None else t["s"] for t in T]
fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
ax[0].hist(W, bins=25, color="#4C78A8"); ax[0].axvline(st.mean(W), color="red", ls="--",
          label=f"rata-rata {idf(st.mean(W), 1)} s"); ax[0].legend()
ax[0].set_xlabel("Waiting time (s, skala simulasi)"); ax[0].set_ylabel("Jumlah task"); ax[0].set_title("Distribusi waiting time")
if c["len"]:
    ls_ = sorted(t["L"] for t in T); q = [ls_[int(len(ls_) * p)] for p in (.25, .5, .75)]
    grp = [[], [], [], []]
    for t, w_ in zip(T, W):
        grp[sum(t["L"] > x for x in q)].append(w_)
    ax[1].bar(range(4), [st.mean(x) if x else 0 for x in grp], color="#F58518")
    ax[1].set_xticks(range(4)); ax[1].set_xticklabels(["Q1\n(terpendek)", "Q2", "Q3", "Q4\n(terpanjang)"])
    ax[1].set_ylabel("Rata-rata waiting (s)"); ax[1].set_title("Waiting per kuartil panjang task")
fig.suptitle("Waiting time — " + ttl); save("grafik_6_waiting_time_"+DETAIL+".png")

# G7 Gantt
plt.figure(figsize=(11, 4.5))
for t in T:
    plt.barh(t["vm"], t["f"] - t["s"], left=t["s"], color=vmcol[t["vm"] % 6], edgecolor="white", linewidth=.3)
plt.yticks(range(nvm), [f"vm-{j} ({vmtype[j % 3]})" for j in range(nvm)]); plt.gca().invert_yaxis()
plt.xlabel("Waktu (s, skala simulasi)"); plt.title("Gantt per VM — " + ttl); save("grafik_7_gantt_vm_"+DETAIL+".png")
print("Selesai. Grafik ada di", OUT)
