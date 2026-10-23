# WebConsole 连接方式不要复用 RoleSelect

- **命中**：`src/views/db-manage/common/webconsole/**` 中 `<RoleSelect>` 的 `v-model` 绑定连接方式（例如 `connectionMode`），而不是数据库角色。
- **为什么**：连接协议和数据库角色是不同语义，复用角色选择器会混淆可选项来源、禁用判据与显示状态。
- **改成**：连接方式使用 `src/views/db-manage/common/webconsole/components/connection-mode-select/Index.vue`，通过 `allowed-modes` 与环境启用模式取交集，通过 `disabled` 锁定切换，通过 `modes-change` 向页面同步可用模式；数据库角色继续使用 `RoleSelect`。
- **不要**：不要把 HTTP / WebSocket 选项传给 `RoleSelect`，不要把环境启用状态当成集群权限或连接成功状态。
- **存量**：目标提交中的 MySQL 页面已使用 `ConnectionModeSelect`；MySQL、TenDBCluster 页面的 `RoleSelect` 均绑定 `role`。
- **核实**：2026-11-03，已阅读目标 MySQL 页面和当前 TenDBCluster 页面源码。
