# TenDBCluster 接入层全毁灾难恢复 — 演练与验收

## 前置条件

- Remote 分片可连通，DBM 元数据（Cluster、分片、Proxy 或端口覆盖）完整。
- 存在可用的 Spider/tdbctl **grant** 独立备份（`data_schema_grant=grant`），或单据选择 `account_rules_only` 并接受仅规则重放。
- 新机器已申请，满足 `check_disaster_tolerance_level`。

## 演练步骤（建议）

1. 在测试集群构造「Spider 全不可达、Remote 正常」场景（防火墙或停机）。
2. 发起 `TENDBCLUSTER_SPIDER_LAYER_DISASTER_RECOVER`，`disable_manual_confirm=false`，核对 **路由预览** 与 `RoutePreview` 摘要表。
3. 确认后继续，观察安装、Remote 授权、表结构、权限、路由、元数据、缩容旧节点各阶段日志。
4. 校验主域名解析、业务读写、周期性 routing 巡检无异常。

## 验收项

- 主域名指向新 Spider IP；元数据仅保留新 Proxy 行。
- 中控 `mysql.servers` 与元数据推导分片关系一致（可与巡检逻辑人工比对）。
- 权限恢复后业务账号可登录 Spider 端口。

## 回滚与人工介入

- 流程失败时停在最近成功子阶段，可重试同一单据（注意幂等：重复 GRANT 一般可接受）。
- **不自动回滚** 已执行的 Remote GRANT；需人工评估后处理。
- `account_rules_only` 不恢复 grant 文件中的历史账号，需另行执行授权规则单据或手工补权。

## 人工介入点

- 路由预览后的 **Pause**（未 `disable_manual_confirm` 时）。
- 缩容旧接入层前的 **PauseWithTicketLockCheck**（与替换接入层单据互斥策略一致）。
