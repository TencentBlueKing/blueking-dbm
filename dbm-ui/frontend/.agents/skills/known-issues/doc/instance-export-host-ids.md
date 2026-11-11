# 实例导出使用主机 ID，不是实例 ID

- **命中**：新增或修改 `DropdownExportExcel` 且 `export-type="instance"`，检查 `:ids` 的来源；若是 `useClusterTableSelect` 的 `selectedIdList`（取 `item.id`），即命中。命令：`rg -n -C 4 'export-type' src/views/db-manage`。
- **为什么**：公共导出组件将实例导出的 `ids` 发给接口的 `bk_host_ids`，传实例 ID 会导出空数据或错误主机上的实例。
- **改成**：从 `useClusterTableSelect<InstanceModel>()` 解构 `selectedHostIdList`，导出绑定 `:ids="selectedHostIdList"`；它由公共 hook 对 `item.bk_host_id` 去重得到。页面不重复计算。其他需要实例 / 集群 ID 的操作继续使用 `selectedIdList`。
- **不要**：不要改变 `selectedIdList` 的取值语义，也不要把公共 hook 的 `bk_host_id` 改成必填，它还有集群和待办调用方。未要求修复的其他页面只报告。
- **存量**：用上面的命令重新列全入口，逐个核实 `ids` 来源。原有 7 处（MySQL HA、Redis 集群版 / 主从版、MongoDB 副本集 / 分片集群、SQL Server HA、Oracle 主备）已统一使用公共 hook 的 `selectedHostIdList`，TenDB Cluster 也已修复；InfluxDB 原本已取 `item.bk_host_id`。当前已排查入口中无剩余实例 ID 混用。
- **核实**：2026-11-11，已核实入口、选择 hook、实例模型与 source 接口参数；未执行类型检查、ESLint 或运行时导出验证。
