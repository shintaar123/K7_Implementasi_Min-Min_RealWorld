"""Grafik makespan vs jumlah task (simulasi Min-Min 6 VM vs nyata di Kubernetes).

Jalankan dari root soka-realworld:
    python real/grafik_makespan.py

Output:
  results_real/grafik/grafik_makespan_gocj.png
  results_real/grafik/grafik_makespan_synthetic.png
  results_real/grafik/grafik_deviasi.png
  results_real/ringkasan_deviasi.csv / .md
Grafik ringkasan lama (grafik_1, 2, 3, 8 dari analisis_lengkap.py) otomatis dihapus;
grafik detail 4-7 (beban VM, urutan, waiting, Gantt) tidak dihapus.
"""
import csv, glob, json, os, re, statistics as st, sys
import numpy as np
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
OUT = os.path.join(ROOT, "grafik")
os.makedirs(OUT, exist_ok=True)
CFG = json.load(open("real/config.json"))
MIPS = [CFG["vm_types"][j % len(CFG["vm_types"])]["mips"] for j in range(CFG["hosts"] * CFG["vms_per_host"])]
LIMIT = 15.0
OVERHEAD = 1.14  # nyata/prediksi*skala, dari run syn1000 & GoCJ

def min_min(length, mips):
    """Port dari controller.py (tie-break sama), versi numpy."""
    L = np.array(length, dtype=float); m = np.array(mips, dtype=float)
    ready = np.zeros(len(m))
    while len(L):
        ct = ready[None, :] + L[:, None] / m[None, :]
        vm = ct.argmin(axis=1)
        best = ct[np.arange(len(L)), vm]
        i = int(best.argmin())
        ready[vm[i]] = best[i]
        L = np.delete(L, i)
    return float(ready.max())

# ---------- dataset yang tersedia ----------
def files():
    d = {}
    for f in glob.glob("data/GoCJ_Dataset_*.txt"):
        n = int(re.search(r"_(\d+)\.txt$", f).group(1)); d[("gocj", n)] = f
    for f in glob.glob("data/Synthetic_*.txt"):
        n = int(re.search(r"_(\d+)\.txt$", f).group(1)); d[("syn", n)] = f
    return d
FILES = files()

# ---------- prediksi simulasi (cache) ----------
cache_path = os.path.join(ROOT, "prediksi_6vm.json")
cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
for (fam, n), f in sorted(FILES.items(), key=lambda x: (x[0][0], x[0][1])):
    key = f"{fam}{n}"
    if key not in cache:
        print(f"hitung prediksi {key} ...", flush=True)
        cache[key] = round(min_min([float(x) for x in open(f) if x.strip()], MIPS), 2)
json.dump(cache, open(cache_path, "w"), indent=1)

# ---------- hasil nyata ----------
def read_summary(p):
    d = {}
    for r in csv.DictReader(open(p, encoding="utf-8-sig")):
        try: d[r["metrik"]] = float(r["nilai"])
        except ValueError: pass
    return d

real = {}   # (fam, n) -> list of dict
for f in sorted(glob.glob(os.path.join(ROOT, "*_minmin_run*", "real_summary.csv"))):
    m = re.match(r"(gocj|syn)(\d+)_minmin_run\d+$", os.path.basename(os.path.dirname(f)))
    if not m: continue
    s = read_summary(f); fam, n = m.group(1), int(m.group(2))
    pred = cache[f"{fam}{n}"]; r = s["makespan_setara_simulasi_detik"]
    real.setdefault((fam, n), []).append(dict(
        real=r, dev=abs(r - pred) / pred * 100, ru=s["resource_utilization_persen"],
        wait=s["average_waiting_time_detik"], thr=s["throughput_task_per_detik"]))

def ms(x): return (st.mean(x), st.stdev(x) if len(x) > 1 else 0.0)
NAME = {"gocj": "GoCJ", "syn": "Synthetic"}
rows = []
for (fam, n) in sorted(real, key=lambda k: (k[0] != "gocj", k[1])):
    g = real[(fam, n)]; rm, rs = ms([x["real"] for x in g]); dm, ds = ms([x["dev"] for x in g])
    um, us = ms([x["ru"] for x in g]); wm, ws = ms([x["wait"] for x in g]); tm, ts = ms([x["thr"] for x in g])
    rows.append(dict(fam=fam, n=n, runs=len(g), pred=cache[f"{fam}{n}"], rm=rm, rs=rs, dm=dm, ds=ds,
                     um=um, us=us, wm=wm, ws=ws, tm=tm, ts=ts))

# ---------- tabel ----------
with open(os.path.join(ROOT, "ringkasan_deviasi.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["dataset", "n_task", "n_run", "prediksi_s", "nyata_mean_s", "nyata_sd_s", "deviasi_mean_%",
                "deviasi_sd_%", "util_mean_%", "util_sd_%", "waiting_mean_s", "waiting_sd_s", "throughput_mean", "throughput_sd"])
    for r in rows:
        w.writerow([f"{NAME[r['fam']]}-{r['n']}", r["n"], r["runs"], r["pred"], round(r["rm"], 2), round(r["rs"], 2),
                    round(r["dm"], 2), round(r["ds"], 2), round(r["um"], 2), round(r["us"], 2),
                    round(r["wm"], 2), round(r["ws"], 2), round(r["tm"], 4), round(r["ts"], 4)])
with open(os.path.join(ROOT, "ringkasan_deviasi.md"), "w", encoding="utf-8") as fh:
    fh.write("| Dataset | Task | Ulangan | Prediksi sim (s) | Nyata setara (s) | Deviasi (%) | Utilization (%) | Avg waiting (s) | Throughput (task/s) |\n")
    fh.write("|---|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        fh.write(f"| {NAME[r['fam']]}-{r['n']} | {r['n']} | {r['runs']} | {r['pred']:.2f} | {r['rm']:.1f} ± {r['rs']:.1f} | "
                 f"{r['dm']:.1f} ± {r['ds']:.1f} | {r['um']:.1f} ± {r['us']:.1f} | {r['wm']:.1f} ± {r['ws']:.1f} | "
                 f"{r['tm']:.3f} ± {r['ts']:.3f} |\n")

# ---------- grafik ----------
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
C_SIM, C_REAL = "#1f77b4", "#d62728"

def makespan_plot(fam, title, fname):
    sim = sorted((int(re.search(r"\d+", k).group()), v) for k, v in cache.items() if k.startswith(fam))
    pts = sorted((r for r in rows if r["fam"] == fam), key=lambda r: r["n"])
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot([a for a, _ in sim], [b for _, b in sim], "-o", color=C_SIM, ms=5, label="Simulasi (prediksi Min-Min, 6 VM)")
    if pts:
        ax.errorbar([r["n"] for r in pts], [r["rm"] for r in pts], yerr=[r["rs"] for r in pts], fmt="-s",
                    color=C_REAL, ms=6, capsize=4, label="Nyata (Kubernetes, setara skala simulasi)")
        for r in pts:
            ax.annotate(idf(r['dm'], 1) + "%", (r["n"], r["rm"]), textcoords="offset points", xytext=(0, 9),
                        ha="center", fontsize=8, color=C_REAL)
    ax.set_xlabel("Jumlah task"); ax.set_ylabel("Makespan (detik, skala simulasi)")
    ax.set_title(title); ax.grid(alpha=.3); ax.legend(loc="upper left", frameon=False)
    ax.set_ylim(bottom=0); ax.margins(x=0.05)
    ax.set_xticks([a for a, _ in sim])
    localize(fig); fig.tight_layout(); fig.savefig(os.path.join(OUT, fname), dpi=200); plt.close(fig)

makespan_plot("gocj", "Makespan vs jumlah task — GoCJ", "grafik_makespan_gocj.png")
makespan_plot("syn", "Makespan vs jumlah task — Synthetic", "grafik_makespan_synthetic.png")

fig, ax = plt.subplots(figsize=(8, 4.8))
for fam, col, mk in (("gocj", C_SIM, "o"), ("syn", C_REAL, "s")):
    pts = sorted((r for r in rows if r["fam"] == fam), key=lambda r: r["n"])
    if pts:
        ax.errorbar([r["n"] for r in pts], [r["dm"] for r in pts], yerr=[r["ds"] for r in pts],
                    fmt="-" + mk, color=col, capsize=4, label=NAME[fam])
ax.axhline(LIMIT, color="gray", ls="--", lw=1, label="Batas 15%")
ax.set_xlabel("Jumlah task"); ax.set_ylabel("Deviasi nyata vs simulasi (%)"); ax.set_ylim(bottom=0)
ax.set_title("Deviasi per jumlah task"); ax.grid(alpha=.3); ax.legend(frameon=False)
localize(fig); fig.tight_layout(); fig.savefig(os.path.join(OUT, "grafik_deviasi.png"), dpi=200); plt.close(fig)

# ---------- hapus grafik lama ----------
for f in glob.glob(os.path.join(OUT, "grafik_[1238]_*.png")):
    os.remove(f); print("hapus", f)
print("Selesai. Grafik di", OUT)
