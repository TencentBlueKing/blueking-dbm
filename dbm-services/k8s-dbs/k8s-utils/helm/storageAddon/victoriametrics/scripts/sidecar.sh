#!/bin/bash
set -o pipefail

# 初始化副本数（从configmap读取）
topo_name=$(kubectl get cluster ${KB_CLUSTER_NAME} -n ${KB_NAMESPACE} -o jsonpath='{.spec.topology}')
echo "当前集群的拓扑类型 : ${topo_name}"

# 检查拓扑名称是否符合条件
if [[ "${topo_name}" != "cluster" ]]; then
  echo "检测到非 cluster 拓扑类型，退出监测 KB_COMP_REPLICAS"
  sleep infinity
fi

previous_replicas=$(kubectl get configmap ${KB_CLUSTER_NAME}-vmstorage-env -n ${KB_NAMESPACE} \
    -o jsonpath='{.data.KB_COMP_REPLICAS}' | awk '{print int($0)}')
echo "初始化vmstorage副本数 : ${previous_replicas}"

while true; do
  # 获取当前副本数（从configmap读取）
  current_replicas=$(kubectl get configmap ${KB_CLUSTER_NAME}-vmstorage-env -n ${KB_NAMESPACE} \
      -o jsonpath='{.data.KB_COMP_REPLICAS}' | awk '{print int($0)}')

  # 处理无效值
  current_replicas=${current_replicas:-$previous_replicas}

  # 检测副本数变化
  if [[ "$current_replicas" -ne "$previous_replicas" ]]; then
    echo "检测到副本数变化 (旧: ${previous_replicas} → 新: ${current_replicas})，触发pod重启..."

    kubectl delete pod ${KB_POD_NAME} -n ${KB_NAMESPACE}

    previous_replicas=$current_replicas
  fi

  sleep 60
done
