# DBHA v2 文档

本文为 `docs/` 总入口。建议阅读顺序：**架构总览 → 工作流程 → 按 DB 探测设计**。

## 1. 架构

| 文档 | 说明 |
| --- | --- |
| [架构总览](architecture/overview.md) | 组件职责、部署拓扑、外部依赖、端到端数据流 |

## 2. 工作流程

| 文档 | 说明 |
| --- | --- |
| [配置下发](flows/config-sync.md) | Probe 从 Admin 拉取配置元信息并在本地渲染 `probe.yaml` |
| [gen-config 设计](flows/gen-config-design.md) | `gen-config` 加锁原子落盘、`--clear-port` 端口裁剪、`--reload` 通知、失败退出码 |
| [采集与上报](flows/probe-harvest-and-report.md) | Harvester 采集 → Reporter（gRPC / GSE）→ Receiver → MySQL |
| [故障判定与切换](flows/failure-detection-and-failover.md) | Analysis：同步元数据、Scan、二次探测条件入窗、滑动窗口、策略匹配、执行切换 |

## 3. 探测设计

| 文档 | 说明 |
| --- | --- |
| [探测设计索引](detection/detection-doc-index.md) | 探测/切换设计文档索引（含 MySQL 家族） |
| [MySQL 探测设计](detection/mysql-detection-design.md) | MySQL 家族探测/切换设计（§5 为入窗语义权威） |

## 4. Admin 配置热重载

Admin 收到 `SIGHUP`（或执行 `admin reload`）后，会先解析并校验配置，再按资源槽依次更新
Discovery、APM 指标服务、Storage、gRPC 和 Web 服务。单个资源更新失败不会阻止配置快照生效，
失败资源会在后续 reload 时重试。`admin reload` 在发送信号前执行一次解析和校验；配置文件缺失时
仍向当前进程的 `pidFile` 发信号，损坏的 yaml 或校验失败则不发信号。

各槽切换窗口：

- **Web**：同址 Replace（先停后起，有短暂空窗）；异址 Coexist（新旧短暂并存）。
- **APM**：同址 Replace（端口不能共存，复用 collector）；异址 Coexist。
- **gRPC**：改地址时先起新监听再关旧；同址改参数时必须等旧 server 停干净后再在同一 listener 上起新
  server，关闭超时则本次不切代。
- **Discovery**：Coexist，新旧注册短暂并存，不是空窗。
- **Storage**：Coexist；退休等待短于 drain 超时时，刚换代立刻再 SIGHUP 可能因退休未完成失败并重试。

`log.level` 可即时生效；日志文件路径、滚动大小和保留数量仍需重启。`name`、`version` 和
`pidFile` 在进程生命周期内保持不变。hanet 监听地址冲突视为该槽启动失败，不会改用外部 listener。

改 probe 下发相关配置会触发全网 harvester 重建，不宜频繁 SIGHUP。

---

返回：[项目 README](../README.md)
