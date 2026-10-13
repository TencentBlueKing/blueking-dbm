# 单据详情与提单入口对齐，复用同族详情展示规范

- **命中**：新增或修改 `src/views/ticket-center/common/ticket-detail/components/task-info/com-factory/**`，涉及 `backupinfo` 或目标规格展示。定位：`rg -n 'col-key="backupinfo"|目标规格' src/views/ticket-center/common/ticket-detail/components/task-info/com-factory`。
- **为什么**：只展示备份 ID、时间及普通标签，会丢失提单页的备份类型颜色、范围、文件大小、关联单据；漏列或改变顺序会使用户无法核对提单内容。
- **改成**：逐项读取对应提单 `Index.vue`，对齐页级项、列头、列序和条件列；备份记录照同 DB 的 `Rollback.vue` / `FixpointExistCluster.vue` 网格展示，区分 MySQL 的 `mysql_role + backup_time` 与 TenDBCluster 的 `backup_consistent_time`，保留类型 `DbTag` 的 `info` / `warning` 主题、备份范围标记、文件大小、关联单据链接。详情壳继续用 `InfoList` 与 `TicketInfoTable`，辅助录入控件及可用资源预览不展示。
- **数据边界**：详情消费单据快照。MySQL 新机回档已确认：角色资源取 `details.apply_details.resource_spec`，名称取 `details.specs[spec_id].name`；`proxy.count` 为台数，`backend_group.count` 为主从组数，按台展示需乘 2，单节点部署的 `backend.count` 为台数。该结构由后端派生，前端提单不需要上送。TenDBCluster 新机回档尚未提供实际响应，不照搬 MySQL 字段。缺少快照显示 `--`，禁止实时查询源集群来冒充历史目标规格。可选备份元信息缺失显示 `--`，不能误报物理备份或 0 B。
- **不要**：直接复用带编辑行为的提单列组件；为对齐详情顺便更改提单行为；把一个硬编码 `--` 的目标规格占位列描述为已实现目标规格展示。
- **存量**：用上述命令重新定位；本次只调整两类 `RollbackNewHost.vue`，其它同族详情只作参考，未同步改动。
- **核实**：2026-10-30，已读取两类新机回档详情、提单备份列与同族 `Rollback.vue`；尚未执行类型或运行时校验。
