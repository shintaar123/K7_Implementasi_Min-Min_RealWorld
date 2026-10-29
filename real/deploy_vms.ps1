# (Re)deploy 6 VM. Jalankan setiap kali worker.py / config.json berubah.
$ErrorActionPreference = "Stop"
python real/gen_manifests.py
kubectl delete -f k8s/vms.yaml --ignore-not-found --wait=true
kubectl delete configmap soka-code --ignore-not-found
kubectl create configmap soka-code --from-file=real/worker.py --from-file=real/controller.py --from-file=real/calibrate.py
kubectl apply -f k8s/vms.yaml
kubectl wait --for=condition=Ready pod -l soka-vm --timeout=300s
kubectl get pods -o wide
