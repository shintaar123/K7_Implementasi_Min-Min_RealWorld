# Jalankan dari root soka-realworld:  .\real\batch_gocj.ps1
# GoCJ 100,200,...,1000 x 3 ulangan. Yang sudah ada otomatis dilewati.
# Contoh lain: .\real\batch_gocj.ps1 -Sizes 200,400 -Runs 1
param(
  [int[]]$Sizes = @(100,200,300,400,500,600,700,800,900,1000),
  [int]$Runs = 3
)
$gagal = @()
$mulai = Get-Date
foreach ($n in $Sizes) {
  $data = "data/GoCJ_Dataset_$n.txt"
  if (-not (Test-Path $data)) { Write-Warning "Dataset tidak ada: $data"; continue }
  for ($r = 1; $r -le $Runs; $r++) {
    $out = "results_real/gocj${n}_minmin_run$r"
    if (Test-Path "$out/real_summary.csv") { Write-Host "[skip] $out sudah ada"; continue }
    Write-Host "=== GoCJ-$n run $r | mulai $(Get-Date -Format HH:mm:ss) ==="
    try {
      & .\real\run_experiment.ps1 -Dataset $data -Algo minmin -Out $out
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
