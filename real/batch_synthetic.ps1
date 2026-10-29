# Jalankan dari root soka-realworld:  .\real\batch_synthetic.ps1
# Contoh: .\real\batch_synthetic.ps1 -Sizes 2000,5000,10000 -Runs 1
param(
  [int[]]$Sizes = @(2000,3000,4000,5000,6000,7000,8000,9000,10000),
  [int]$Runs = 1
)
$gagal = @()
$mulai = Get-Date
foreach ($n in $Sizes) {
  for ($r = 1; $r -le $Runs; $r++) {
    $out = "results_real/syn${n}_minmin_run$r"
    if (Test-Path "$out/real_summary.csv") { Write-Host "[skip] $out sudah ada"; continue }
    Write-Host "=== Synthetic-$n run $r | mulai $(Get-Date -Format HH:mm:ss) ==="
    try {
      & .\real\run_experiment.ps1 -Dataset "data/Synthetic_$n.txt" -Algo minmin -Out $out
      if (-not (Test-Path "$out/real_summary.csv")) { throw "real_summary.csv tidak ada" }
    } catch {
      Write-Warning "GAGAL $out : $_"
      $gagal += $out
    }
  }
}
$menit = [math]::Round(((Get-Date) - $mulai).TotalMinutes, 1)
Write-Host "`nSelesai dalam $menit menit."
if ($gagal.Count) { Write-Warning ("Gagal: " + ($gagal -join ", ") + " -> jalankan skrip lagi, yang sudah jadi otomatis dilewati.") }
else { Write-Host "Semua sukses. Lanjut: python real/grafik_makespan.py" }
