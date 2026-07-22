# DBHA v2 工作流程

本目录描述端到端主路径，配合 [架构总览](../architecture/overview.md) 阅读。

## 流程列表


| 文档                                           | 说明                                                    |
| -------------------------------------------- | ----------------------------------------------------- |
| [配置下发](config-sync.md)                       | Probe 主动从Admin Server 拉取配置元信息后自动在本地渲染配置文件             |
| [采集与上报](probe-harvest-and-report.md)         | Harvester 采集 → Reporter（gRPC / GSE）→ Receiver → MySQL |
| [故障判定与切换](failure-detection-and-failover.md) | Analysis：同步元数据、Scan、滑动窗口、策略匹配、执行切换                    |


按 DB 类型下钻的探测/切换设计（数据结构、探测 SQL、事件、切换）见 [探测设计文档索引](../detection/detection-doc-index.md)。

## 端到端串联

```text
config-sync → probe-harvest-and-report → failure-detection-and-failover
     │                    │                          │
  Admin 下发配置      状态写入 t_dbha_status      读状态并切换
```

返回：[项目 README](../../README.md) · [架构总览](../architecture/overview.md)