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

---

返回：[项目 README](../README.md)
