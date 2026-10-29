# Contoh: .\real\run_experiment.ps1 -Dataset data/GoCJ_Dataset_100.txt -Algo minmin -Out results_real/gocj100_minmin_run1
param(
  [string]$Dataset = "data/GoCJ_Dataset_100.txt",
  [ValidateSet("minmin","roundrobin")][string]$Algo = "minmin",
  [string]$Out = "results_real/run1"
)
$ErrorActionPreference = "Stop"
kubectl delete pod soka-controller --ignore-not-found --wait=true
kubectl delete configmap soka-cfg soka-data soka-code --ignore-not-found
kubectl create configmap soka-code --from-file=real/worker.py --from-file=real/controller.py --from-file=real/calibrate.py
kubectl create configmap soka-cfg  --from-file=config.json=real/config.json
kubectl create configmap soka-data --from-file=dataset.txt=$Dataset
(Get-Content k8s/controller.yaml) -replace 'value: minmin', "value: $Algo" | kubectl apply -f -
kubectl wait --for=condition=Ready pod/soka-controller --timeout=300s

while ($true) {
    Start-Sleep -Seconds 5
    $phase = kubectl get pod soka-controller -o jsonpath='{.status.phase}'
    $log = kubectl logs soka-controller 2>$null
    if ($log -match '# selesai') { break }
    if ($log -match '# GAGAL' -or $phase -eq 'Failed') { $log; throw "Controller gagal, lihat log di atas." }
}
$log | Select-String '^#'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
kubectl cp soka-controller:/results/real_summary.csv        "$Out/real_summary.csv"
kubectl cp soka-controller:/results/real_cloudlet_result.csv "$Out/real_cloudlet_result.csv"
Write-Host "Hasil tersimpan di $Out"
