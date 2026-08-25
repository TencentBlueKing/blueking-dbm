# 流程：Probe 配置下发

Probe 不在本地硬编码业务元数据，而是通过 Admin 的 `GetProbeConfig` 拉取配置元数据，再在本机渲染为最终的配置文件 `probe.yaml`。

相关文档：[架构总览](../architecture/overview.md) · [采集与上报](probe-harvest-and-report.md) · [文档索引](../README.md)

## 1. 参与方

| 角色 | 说明 |
| --- | --- |
| **dbha-probe** | 命令行子命令 `gen-config` 触发，通过 gRPC 调用获取元数据 |
| **dbha-admin** | 提供 gRPC API 供 probe 调用获取元数据 |
| **MySQL / DBM** | 元数据优先读 DBHA 本地库；未查到则回退调用 DBM API |

## 2. 工作原理

Probe 经 Admin 拉取 `ProbeConfigPayload` 后在本机渲染为 `probe.yaml`。

配置全量刷新以 `GetProbeConfig` / `gen-config` 为主；运行期 `Heartbeat`（见 [admin.proto](../../pkg/proto/idl/admin.proto)）侧重轻量 ack，当前无配置增量，不替代全量下发。写入 `probe.yaml` 后可用 `gen-config -o ... --reload` 或 `dbha-probe reload` 通知运行中的 probe 热加载（见 [gen-config-design.md](gen-config-design.md) §5.5）。

```mermaid
sequenceDiagram
  participant Probe as dbha_probe
  participant Admin as dbha_admin
  participant Meta as MySQL_or_DBM

  Probe->>Admin: GetProbeConfig(bkCloudId, ip, clientID)
  Note over Probe,Admin: bkCloudId+ip 参与 GenProbeConfig；clientID 仅日志

  Admin->>Meta: loadProbeMetadata
  Note over Admin,Meta: 优先本地 DBHA 库；无数据回退 DBM API

  alt 无元数据
    Admin-->>Probe: PROBE_CONFIG_NO_DATA
    Note over Probe,Admin: 该 ip 无可用元数据，下发失败
  else 有元数据
    Admin->>Admin: GenProbeConfig 组装 ProbeConfigPayload
    Note over Admin: payload：GSE 默认块 + 探测元数据 + Harvester 公共配置
    Admin-->>Probe: ProbeConfigResponse.payload JSON
    Note over Admin,Probe: gRPC 返回 JSON 字符串

    Probe->>Probe: genconfig 渲染 probe.yaml
    Note over Probe: 供本机 harvester/reporter；改 gRPC 上报见采集与上报
  end
```

代码入口：[GenProbeConfig](../../internal/admin/config/probe_config.go) · [pkg/probeconfig](../../pkg/probeconfig) · [genconfig](../../internal/probe/config/genconfig.go)

## 3. 关键代码路径

| 步骤 | 路径 |
| --- | --- |
| Proto | [pkg/proto/idl/admin.proto](../../pkg/proto/idl/admin.proto) |
| gRPC 处理 | [internal/admin/grpc.go](../../internal/admin/grpc.go)（`GetProbeConfig` / `Heartbeat`） |
| 配置生成 | [internal/admin/config/probe_config.go](../../internal/admin/config/probe_config.go) |
| Payload 类型 | [pkg/probeconfig/metadata.go](../../pkg/probeconfig/metadata.go) |
| Probe CLI / 渲染 | [internal/probe/cmds](../../internal/probe/cmds)、[internal/probe/config/genconfig.go](../../internal/probe/config/genconfig.go) |

## 4. 运维注意

- 元数据为空时返回 `PROBE_CONFIG_NO_DATA`，需先保证 analysis 同步或 DBM 侧有该 IP 的实例信息。
- 部署侧常用 `dbha-probe gen-config` 后再 `start` / `daemon-start`；自动化见 scripts 与 `ensure` 子命令。
- 运行中更新配置：在安装根目录执行 `dbha-probe gen-config -o <probe.yaml 路径> --reload`（或改完文件后执行 `dbha-probe reload`），使 probe 热加载新 YAML。
- Admin 下发默认 reporter 为 GSE；运行时 gRPC / GSE 二选一与改法见 [采集与上报](probe-harvest-and-report.md)。
