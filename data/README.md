# Dataset

Folder ini berisi dua jenis dataset yang digunakan untuk pengujian simulasi penjadwalan:

### 1. Dataset GoCJ (100–1.000 task)
File: `GoCJ_Dataset_100.txt` s.d. `GoCJ_Dataset_1000.txt` (kelipatan 100).
- Sumber: GoCJ (Google Cloud Jobs) - Hussain & Aleem (2018), *Data* 3(4):38, doi.org/10.3390/data3040038.
- Format: Satu angka panjang task (MI) per baris.
- Rentang task: 15.000 s.d. 900.000 MI.

### 2. Synthetic Dataset (1.000–10.000 task)
File: `Synthetic_1000.txt` s.d. `Synthetic_10000.txt` (kelipatan 1.000).
- Dihasilkan via `tools/make_synthetic.py`.
- Format: Satu angka panjang task (MI) per baris.
- Distribusi heterogen:
  - 60% task kecil (10.000 – 50.000 MI)
  - 30% task sedang (50.000 – 150.000 MI)
  - 10% task besar (150.000 – 500.000 MI)

### Catatan
- Untuk membuat ulang Synthetic Dataset, jalankan: `python3 tools/make_synthetic.py`.
