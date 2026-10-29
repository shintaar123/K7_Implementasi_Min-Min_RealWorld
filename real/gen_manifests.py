import json, os
cfg = json.load(open("real/config.json"))
os.makedirs("k8s", exist_ok=True)
docs = []
for h in range(cfg["hosts"]):
    for t in range(cfg["vms_per_host"]):
        vm = h * cfg["vms_per_host"] + t
        ty = cfg["vm_types"][vm % len(cfg["vm_types"])]    # sama dengan SimConfig.vmTypeIndex
        cpu = ty["mips"] / cfg.get("mips_per_core", 4000)
        milli = int(round(cpu * 1000))
        docs.append(f"""apiVersion: v1
kind: Pod
metadata:
  name: vm-{vm}
  labels: {{soka-vm: "{vm}"}}
spec:
  nodeSelector: {{soka-host: host-{h+1}}}
  containers:
  - name: worker
    image: python:3.11-slim
    imagePullPolicy: IfNotPresent
    command: ["python", "/app/worker.py"]
    ports: [{{containerPort: 8080}}]
    env:
    - {{name: VM_ID, value: "{vm}"}}
    - {{name: VM_MIPS, value: "{ty['mips']}"}}
    - {{name: CPU_LIMIT, value: "{cpu}"}}
    - {{name: TIME_SCALE, value: "{cfg['time_scale']}"}}
    - {{name: OPS_PER_MI, value: "{cfg['ops_per_mi']}"}}
    - {{name: MODE, value: "{cfg.get('mode', 'cpu')}"}}
    - {{name: MIPS_PER_CORE, value: "{cfg.get('mips_per_core', 4000)}"}}
    - {{name: NODE_NAME, valueFrom: {{fieldRef: {{fieldPath: spec.nodeName}}}}}}
    resources:
      requests: {{cpu: "{milli}m", memory: 256Mi}}
      limits:   {{cpu: "{milli}m", memory: 256Mi}}
    volumeMounts: [{{name: code, mountPath: /app}}]
  volumes: [{{name: code, configMap: {{name: soka-code}}}}]
---
apiVersion: v1
kind: Service
metadata: {{name: vm-{vm}}}
spec:
  selector: {{soka-vm: "{vm}"}}
  ports: [{{port: 8080, targetPort: 8080}}]""")
open("k8s/vms.yaml", "w", newline="\n").write("\n---\n".join(docs) + "\n")

open("k8s/controller.yaml", "w", newline="\n").write("""apiVersion: v1
kind: Pod
metadata: {name: soka-controller}
spec:
  nodeSelector: {"node-role.kubernetes.io/control-plane": ""}
  tolerations: [{key: "node-role.kubernetes.io/control-plane", operator: Exists, effect: NoSchedule}]
  containers:
  - name: controller
    image: python:3.11-slim
    imagePullPolicy: IfNotPresent
    command: ["sh", "-c", "python /app/controller.py && sleep 3600"]
    env:
    - {name: DATASET, value: /data/dataset.txt}
    - {name: ALGO, value: minmin}
    volumeMounts:
    - {name: code, mountPath: /app}
    - {name: cfg,  mountPath: /cfg}
    - {name: data, mountPath: /data}
  volumes:
  - {name: code, configMap: {name: soka-code}}
  - {name: cfg,  configMap: {name: soka-cfg}}
  - {name: data, configMap: {name: soka-data}}
""")
print("manifest dibuat di k8s/")
