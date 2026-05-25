# DBHA-v2 Change Log

## v2.0.0-beta.7
- 【新增】Probe 维护/查询 `master_slave_heartbeat`，上报mysql实例心跳状态以及mysql slave的心跳延迟。
- 【新增】将切换请求的快照写入单独的日志文件中。
- 【优化】将 `DbmMetadataInstanceRole`、`DbmMetadataSpiderRole` 从 `internal/analysis/dbm` 迁至 `pkg/storage/haprobe`，便于统一引用。
- 【优化】对于切换流程中对mysql slave的延迟、checksum等检查项，支持在配置文件中设置相关参数。
- 【优化】移除切换日志中的密码明文。
- 【修复】过滤白名单集群字段改为 clusterName, 与 v1 保持一致。

## v2.0.0-beta.6
- 【新增】DBM API 调用统计。
- 【新增】探针（Probe）新增 Keepalive 工作模式，用于辅助二次探测检测主机的存活状态。
- 【新增】运维脚本增加 crontab 守护配置，启动进程时自动注册 crontab 守护，stop 时自动删除 crontab 守护配置。
- 【优化】切换流程支持可配置的整体截止时间（`workflow.switchTimeout`），默认值为 10m，未配置有效值时，回退上限亦为 10m。
- 【优化】切换链路支持分段超时配置，新增下列项及默认值：
  - 写切换日志到 DB（`switchflow.switchLogWriteTimeout`）：1s。
  - 与 DB 实例建立连接（`switchflow.dbConnectTimeout`）：3s。
  - 切换时的集群锁等待（`switchflow.clusterLockTimeout`）：60s。
  - 切换步骤内的 SQL 执行时长（`switchflow.execSqlTimeout`）：6s。
- 【优化】切换调度默认值调整：滑动窗口时长（`workflow.windowDuration`）由 10s 调整为 0。
- 【优化】切换时访问 DBM 的并发请求上限（`switchflow.dbmApiMaxConcurrentRequests`）由 16 调整为 8。
- 【修复】cluster 工具在并行调用 DBM 时，因共用 HTTP 客户端致使各请求超时参数相互覆盖的问题。
- 【修复】滑动窗口 metric 统计的数据残留问题。

## v2.0.0-beta.5
- 【优化】Pop And Switch 与白名单功能启用进行参数化改造，支持配置文件配置。
- 【优化】优化业务扫描算法，支持多业务并行扫描，减少当前业务扫描未执行完而阻塞下一次扫描启动的影响。
- 【优化】优化 DB 元数据统计策略，统计所有 DB 类型的有效元数据数量。
- 【优化】优化探针侧探针插件接口的定义，去掉无效的函数（Version()）。
- 【优化】优化从 DBM 同步 DB 元数据的解析逻辑，兼容 spider_role 和 instance_role 未被同时赋值导致 instance_role 为空值的问题。
- 【修复】修复探针渲染 spider slave 配置时的算法，如果节点为 spider slave，则不生成中控相关的配置，如：admin ports。
- 【修复】修复白名单应用策略，AM 仅对白名单的业务或集群触发切换。

## v2.0.0-beta.4
- 【新增】过去 5 分钟内上报状态数据的探针数量统计以及 DB 实例元数据数量统计。
- 【优化】Probe 配置渲染流程优化，支持独立配置 MySQL、Proxy、Redis 的采集账号。
- 【优化】Analysis 服务优化集群切换时的并行工作流程，提升整体故障切换效率。

## v2.0.0-beta.3
- 【优化】禁用 etcd client 自动同步 etcd 的 member 信息，避免通过 VIP + TLS 访问 ETCD 时出现未授权的报错。

## v2.0.0-beta.2
- 【优化】优化 AM 服务启动流程，避免不必要的启动阻塞。
- 【优化】优化服务监听默认参数配置。
- 【修复】修复部分 metric 统计数据错误的问题。

## v2.0.0-beta.1
- 【新增】实现 MySQL 故障诊断以及基于业务维度的故障切换。
- 【新增】实现 MySQL 实例维度、主机维度以及集群维度的故障切换。
- 【新增】故障切换策略管理。
- 【新增】基于探针的 DB 状态数据采集。