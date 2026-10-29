# Bukti port Min-Min benar: bandingkan hasil Python dengan hasil Java (cloudlet_result.csv).
# Pakai (dari root repo): python real/crosscheck.py data/GoCJ_Dataset_300.txt results/cloudlet_result.csv
import csv, os, sys
os.environ.setdefault("CFG", "real/config.json")
os.environ["DATASET"] = sys.argv[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import controller as c

task_vm, order, predicted = c.min_min(c.LENGTH, c.MIPS)
rows = list(csv.DictReader(open(sys.argv[2])))
java_vm  = {int(r["cloudlet_id"]): int(r["vm_id"]) for r in rows}
java_ord = {int(r["cloudlet_id"]): int(r["urutan_dijadwalkan"]) for r in rows}   # Java: mulai dari 1
pos = {t: k + 1 for k, t in enumerate(order)}
same_vm  = sum(task_vm[i] == java_vm[i] for i in range(c.N))
same_ord = sum(pos[i] == java_ord[i] for i in range(c.N))
print(f"task={c.N} | VM sama={same_vm}/{c.N} | urutan sama={same_ord}/{c.N} | prediksi Python={predicted:.2f} s")
ok = (len(rows) == c.N and same_vm == c.N and same_ord == c.N)
print("HASIL:", "LULUS (identik dengan Java)" if ok else "GAGAL (cek jumlah VM/tie-break)")
sys.exit(0 if ok else 1)
