# DBHA-v2 Change Log

## v2.0.1-beta.1
【新增】Probe 对 MySQL 按 default / heartbeat / repldelay 三类异步采集：default 按原间隔上报全量状态。
【新增】heartbeat 按较短间隔写 infodba_schema.dbha_heartbeat（sql_log_bin=OFF，只验本机可写）。
【新增】repldelay 按独立间隔写 infodba_schema.dbha_repl_heartbeat（sql_log_bin=ON，复制到从库并据此报延迟）。
【新增】三类采集最终都落入同一张 t_dbha_status，主键增加必填字段 harvest_type 区分类别；Redis 上报补 default。
【优化】Analysis 切换流程中从库延迟时长计算改为查探针表 dbha_repl_heartbeat，只校验 heartbeat_delay，去掉 io_delay 及配置 slaveAllowedMaxIODelay。
【优化】写 dbha_heartbeat 失败会报事件dbha_heartbeat_write_failure，Analysis 据此做 SSH 二次探测；同实例多条事件按实例去重，避免重复探测。
【修复】快照日志表将集群名称与集群ID字段与实例绑定，修复多个集群时名称展示错误问题。
【修复】dbha-cluster show nodes 展示节点信息时排除同机不同集群的实例。

## v2.0.0

- 【新增】增加 proxy 节点非管理端口写心跳功能。
- 【新增】新增兼容 v1 的 SwitchLog 查询 API（/api/admin/switchqueue/、/api/admin/switchlogs/）。
- 【新增】Probe 支持跨平台运行 Linux/Windows。
- 【优化】整机切换针对 remote 多分片场景优化，同集群 remote 实例共享集群锁解决锁等待超时。
- 【优化】优化切换快照日志的写入流程与数据结构，完善 BkIdcID，Status，NewMasterIP，NewMasterPort 字段内容。
- 【优化】完善快照日志信息的检查开始和检查结束时间，同时填充切换日志列表接口数据。
- 【修复】排除策略匹配中不可用状态的实例。

## v2.0.0-beta.12

- 【新增】增加 proxy 节点非管理端口写心跳功能。
- 【新增】新增兼容 v1 的 SwitchLog 查询 API（/api/admin/switchqueue/、/api/admin/switchlogs/）。
- 【新增】Probe 支持跨平台运行 Linux/Windows。
- 【优化】整机切换针对 remote 多分片场景优化，同集群 remote 实例共享集群锁解决锁等待超时。
- 【优化】优化切换快照日志的写入流程与数据结构，完善 BkIdcID，Status，NewMasterIP，NewMasterPort 字段内容。
- 【优化】完善快照日志信息的检查开始和检查结束时间，同时填充切换日志列表接口数据。
- 【修复】排除策略匹配中不可用状态的实例。

## v2.0.0-beta.11

- 【新增】切换请求的响应结果新增mysql存储主节点切换后的新主信息。
- 【新增】MySQL 切换成功告警事件补齐与 DBHA v1 兼容的维度字段。
- 【新增】探针增加对MySQL Proxy 节点 非admin端口的数据采集与探测。
- 【新增】基于gRPC实现Probe与Receiver之间的数据链路。
- 【新增】增加 t_db_switching_snapshot_log 切换快照日志表，并在 Switch 函数切换前与切换后，完善了日志表和本地日志文件的快照数据写入流程。
- 【优化】AM 服务二次探测的指令改为可配置且增加探测指令的安全校验。
- 【修复】mysql sinker 无超时控制导致的探针数据持久化阻塞问题。
- 【修复】修复主从复制异常场景下 slave 延迟上报不准确的问题。



## v2.0.0-beta.10

- 【新增】cluster 工具 `reset` 流程支持 CLB 实例恢复：自动注册缺失实例、注销多余实例。
- 【新增】cluster 工具新增 `show clb` 子命令，支持以 JSON 格式输出 tendbha、tendbcluster 集群的 CLB 绑定信息。
- 【新增】黑白名单管理工具 `bwmgr` 命令行工具。
- 【修复】切换流程中 CLB 实例注销、TBinlogDumper 切换补充 DBM API 响应解析与结果校验。
- 【优化】业务扫描前按白名单集群过滤，仅对白名单内实例发起探测；白名单查询失败时跳过该业务扫描。
- 【优化】白名单查询重试逻辑以及过滤切换实例逻辑迁移至 `dbhav1_whitelist.go`，白名单匹配字段由 clusterName 调整为 clusterId。



## v2.0.0-beta.9

- 【优化】升级grpc and x/crypto版本。
- 【优化】切换流程里修复 Tdbctl 主从同步关系时采用位点同步方式。
- 【修复】白名单查询增加重试逻辑，若最终仍查询失败，丢弃采集的故障实例，不进行切换。



## v2.0.0-beta.8

- 【新增】通过 DBHA v1 提供的查询 API，与 DBHA v1 共享同一个白名单。



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

