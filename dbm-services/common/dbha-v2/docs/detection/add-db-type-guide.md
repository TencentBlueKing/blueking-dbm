# 新增 DB 类型扩展指南

本文说明在 dbha-v2 中新增一种数据库类型时，应如何按 **Provider 集中扩展** 模式开发，避免在框架各处散落改动。

## 目标形态

新增一个 DB 类型时只需：

1. **框架共享类型定义**（无法下沉到 provider）：在 [`pkg/storage/haprobe`](../../pkg/storage/haprobe) 补 `DbType`、`DbmMetadataClusterType`、切换告警用的 `DbEventName` 常量，并新建 `<db>_status.go` 实现 `DBTyper`（仅 `GetDbType() DbType`）
2. 新建 `internal/provider/<db>/`（按能力分子包：`dbtypedesc` / `harvest` / `switch` / `parse`）
3. 在**单一清单** [`internal/provider/manifest.go`](../../internal/provider/manifest.go) 加一条并执行 `go generate ./internal/provider/...`
4. （可选）在 `admin.yaml` 的 `probeHarvesters` 加凭证块
5. （可选）在 analysis config 增加对应 `DbmApi*` 字段

除第 1 步的共享类型定义外，二进制入口与框架分派/列表/config 结构体**不再手改**。

## 能力子包

| 子包 | 职责 | 链接进 |
| --- | --- | --- |
| `dbtypedesc` | 注册 `ClusterType -> DbType`，以及（新 DB）`HarvestBlock` | probe + analysis + admin/receiver（via `alldesc`） |
| `harvest` | 注册采集 Factory | 仅 probe |
| `switch` | 注册切换器 + 切换告警事件名 | 仅 analysis |
| `parse` | 注册 status parser（`parser.Register`） | 仅 analysis |

### Builtin 弱注册

[`pkg/dbtype/builtin.go`](../../pkg/dbtype/builtin.go) 为全部已知类型提供**占位映射**（含 MySQL 与尚未实现采集/切换的类型）。Provider 通过 `dbtype.Register` 注册同名 `DbType` 时会**自动接管**占位；接管时 provider 的 `ClusterTypes` 必须是占位集合的超集，否则 panic。新增 provider **无需改** `builtin.go`。

Redis 故意不在 builtin 中，作为纯 provider 范例；其映射在 `provider/redis/dbtypedesc`。

## 导入收敛

编辑 [`manifest.go`](../../internal/provider/manifest.go) 中的 `Entries`：

```go
{
    Name:     "kafka",
    BasePath: providerRoot + "/kafka",
    Caps:     []Capability{CapDesc, CapHarvest, CapSwitch, CapParse},
},
```

**注意**：填了 `CapParse` / `CapHarvest` / `CapSwitch` / `CapDesc` 就必须建对应子包，否则生成的 import 指向不存在的包会编译失败。

然后：

```bash
go generate ./internal/provider/...
# 或
make check-generate
```

生成物：

- `provider/allprobe`：注入 `dbtypedesc` + `harvest`
- `provider/allanalysis`：注入 `dbtypedesc` + `switch`(+`parse`)
- `provider/alldesc`：仅注入 `dbtypedesc`（供 admin / receiver）

`cmd/probe` / `cmd/analysis` / `cmd/admin` / `cmd/receiver` 各 blank-import 一次对应聚合包，之后不再改。

## 块名规范

- 所有 harvester 块名经 `dbtype.NormalizeBlockName`（小写）归一。
- camelCase 块名允许（如 `myNewDb`），查找按小写匹配（`mynewdb`）。
- Admin `probeHarvesters` 的键同理：viper 装载后已是小写；provider 声明的 `PayloadKey` / `BlockName` 即使保留 camelCase，probe 侧查找也会归一后命中。
- 建议新块优先使用全小写键，减少跨进程键大小写心智负担。

## HarvestBlock Match 谓词

同一 `DbType` 可注册多块。`Match func(EndpointAttrs) bool`：

- 非 nil：按端点属性（clusterType / machineType / instanceRole / accessLayer）优先匹配
- nil：该 DbType 的兜底块；同一 DbType **至多一个**兜底块

路由顺序：先扫 Match 命中，再落兜底；都无匹配则跳过并打日志。

## 采集与配置

- Probe 运行时配置：命名块 `mysql` / `mysqlProxyAdmin` / `redis` 保持零回归；新 DB 走 `HarvesterConfig.Extra`（YAML 同级键）。
- Admin 下发：命名 `probeMysql` / `probeRedis` / `probeProxyAdmin` 不变；新 DB 凭证写入 `probeHarvesters`，admin **纯 pass-through** 到 payload `harvesters`（不 import provider 业务包，只 blank-import `alldesc`）。
- Probe `genconfig`：mysql/redis 仍走命名路由；其它已注册 `HarvestBlock` 的类型走 `extra[BlockName]`。

## 切换与解析

- 在 `provider/<db>/switch` 的 `init()` 中调用 `switcher.Register` 与 `dbtype.RegisterSwitchAlarmEvents`（顺序：先 Register switcher 再注册告警亦可；启动期 `switcher.Validate()` 会校验告警事件已注册）。
- 在 `provider/<db>/parse` 的 `init()` 中调用 `parser.Register(dbType, processer)`。
- 未注册的 `DbType` 在 `TriggerSwitching` 中告警跳过（行为不变）。
- 新主信息字段 `MySqlNewMasterInfo` 仍为 MySQL 专属；新 DB 暂不经该字段返回新主信息。

## Provider 骨架示例（kafka）

以下为可直接复制的最小骨架（需先完成 haprobe 常量与 `kafka_status.go`）。

**`provider/kafka/dbtypedesc/desc.go`**

```go
package dbtypedesc

import (
    "dbm-services/common/dbha-v2/pkg/dbtype"
    "dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func init() {
    dbtype.Register(dbtype.Descriptor{
        DbType: haprobe.DbTypeKafka,
        ClusterTypes: []haprobe.DbmMetadataClusterType{
            haprobe.DbmMetadataClusterTypeKafka,
        },
    })
    dbtype.RegisterHarvestBlock(dbtype.HarvestBlock{
        BlockName:  "kafka",
        DbType:     haprobe.DbTypeKafka,
        PayloadKey: "kafka",
    })
}
```

**`provider/kafka/harvest/register.go`** — `harvester.Register(Entry{BlockName:"kafka", ...})`

**`provider/kafka/switch/register.go`** — `switcher.Register` + `dbtype.RegisterSwitchAlarmEvents`

**`provider/kafka/parse/register.go`** — `parser.Register(haprobe.DbTypeKafka, &KafkaStatus{})`

**manifest 条目**

```go
{Name: "kafka", BasePath: providerRoot + "/kafka",
 Caps: []Capability{CapDesc, CapHarvest, CapSwitch, CapParse}},
```

## 非对称性说明

| 能力 | MySQL 现状 | 新 DB 要求 |
|------|------------|------------|
| parse | 实现 + 注册均在 `provider/mysql/parse` | 同左 |
| switch | 实现在 `switcher`；`provider/mysql/switch` 只注册 | 实现与注册放在 `provider/<db>/switch` |
| harvest | 已在 `provider/mysql/harvest` | 同左 |

框架包 `internal/analysis/parser` 仅保留 `Processer` 接口与注册表；analysis 启动要求 parser 注册表非空（当前由 MySQL `CapParse` 满足）。

## 自检清单

- [ ] haprobe 常量与 `DBTyper` 实现已补齐
- [ ] `manifest.go` 已加条目且 `go generate` 后聚合包含预期 blank-import
- [ ] 每个 Cap 对应子包真实存在（`make check-generate` + manifest 一致性测试）
- [ ] probe / analysis / admin / receiver 二进制可编译
- [ ] catalog / provider import 单测通过
- [ ] 若有采集：admin `probeHarvesters` + HarvestBlock 已配置；块名大小写符合规范
- [ ] 若有多块：Match 谓词与至多一个兜底块已验证
- [ ] 若有切换：switcher + 告警事件名已注册；启动自检通过
- [ ] 若有解析：`parser.Register` 已调用；analysis 启动日志 `parser_db_types` 非空
