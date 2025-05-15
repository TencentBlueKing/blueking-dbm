#!/bin/bash
set -o pipefail

# 初始化副本数（从configmap读取）
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

  sleep 30
done
