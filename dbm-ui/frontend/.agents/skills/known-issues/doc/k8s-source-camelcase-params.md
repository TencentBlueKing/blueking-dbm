# K8s source 的 retrieve / topo / log / spec / toolbox 请求参数保持 camelCase

- **命中**：改 `src/services/source/qdrantHa.ts`、`src/services/source/surrealdbHa.ts`、
  `src/services/source/surrealdbSingle.ts`、`src/services/source/kubernetesToolbox.ts` 的请求参数名时。检索：
  `rg -n 'clusterName|k8sClusterName|componentName|podName' src/services/source/qdrantHa.ts src/services/source/surrealdbHa.ts src/services/source/surrealdbSingle.ts src/services/source/kubernetesToolbox.ts`
- **为什么**：这些字段是 K8s 后端的约定，`http` 按 key 原样序列化。改成 `cluster_name` /
  `k8s_cluster_name` 后过滤条件带不上，详情 / 拓扑 / 日志 / 规格会空或错
- **改成**：保持现有 camelCase（`clusterName`、`k8sClusterName`、`componentName`、`podName`），并在参数定义旁写
  `K8s 后端约定，保持 camelCase`。同文件 `list_instances` 用的 `cluster_name` / `k8s_cluster_name` 也不要改，两套并存。
  备注是否写了：`rg -n 'K8s 后端约定' src/services/source/qdrantHa.ts src/services/source/surrealdbHa.ts src/services/source/surrealdbSingle.ts src/services/source/kubernetesToolbox.ts`
- **不要**：为了和 Django 风格或 `list_instances` 对齐，把 retrieve / topo / log / spec / toolbox 改成
  snake_case
- **存量**：`rg -n 'clusterName|k8sClusterName|componentName|podName' src/services/source/qdrantHa.ts src/services/source/surrealdbHa.ts src/services/source/surrealdbSingle.ts src/services/source/kubernetesToolbox.ts`
- **核实**：2026-09-11
