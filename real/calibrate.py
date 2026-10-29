import os, time
cpu, scale = float(os.environ["CPU_LIMIT"]), float(os.environ["TIME_SCALE"])
mpc = float(os.environ.get("MIPS_PER_CORE", "4000"))

def burn(n):                           # HARUS identik dengan burn() di worker.py (fungsi, variabel lokal)
    x = 0.0
    for i in range(n):
        x += i * 0.5
    return x

N = 5_000_000
burn(200_000)                          # pemanasan
rates = []
for _ in range(3):                     # 3x ukur, ambil median
    t = time.time(); burn(N); rates.append(N / (time.time() - t))
rate = sorted(rates)[1]
r1 = rate / cpu                        # operasi/detik untuk 1 core penuh
print(f"ops/s pod ini = {rate:,.0f}  | setara 1 core = {r1:,.0f}")
print(f"OPS_PER_MI = {scale * r1 / mpc:.2f}")
