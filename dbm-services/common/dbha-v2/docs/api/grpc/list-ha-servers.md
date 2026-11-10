# HA Server 列表（gRPC）

列出当前存活的 admin、analysis、receiver 实例，以及所有实例 IP 去重后的列表。
结果不包含 probe，只读取默认注册根 `/dbha/registry`，不支持自定义根路径。

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| 协议 | gRPC（明文，无 TLS） |
| 地址 | `<grpc.listenAddress>` |
| 方法 | `AdminService/ListHaServers`，完整方法名为 `/AdminService/ListHaServers` |
| 依赖 | 只依赖 etcd，不依赖 storage；存储拦截器直接放行这个方法 |
| 鉴权 | 无 |
| 超时 | `discovery.serviceUpdateTimeout`（rc 变量 `ADMIN_DISCOVERY_SERVICE_UPDATE_TIMEOUT`），见下方说明 |
| 消息大小 | 收发上限默认 10 MiB，由 `grpc.maxReceiveMessageSize`、`grpc.maxSendMessageSize` 配置 |
| 引入版本 | issue #21530 |

- 默认端口为 50051，示例地址为 `127.0.0.1:50051`。
- **注意**：rc 变量为空、按默认渲染部署时，Admin gRPC 监听在探测到的本机 IPv4 上，而不是 `127.0.0.1`。
  执行示例前要把 `127.0.0.1` 换成 `admin.yaml` 中 `grpc.listenAddress` 的实际 host，端口也以配置为准。
  地址的来源见 [接口文档索引](../README.md#3-服务地址)。
- 超时：服务端未配置或配置不大于 0 时为 3 秒，三个角色前缀共用这一个超时。
  调用方自己设置的 deadline 更短时，以调用方为准。

## 2. 请求参数

请求消息 `ListHaServersRequest` 是空消息，没有字段。

| 字段号 | 参数名 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 无 | 无 | 无 | 无 | 无 | 空消息 |

### 请求 JSON 样例

grpcurl `-d` 使用的 JSON：

```json
{}
```

## 3. 返回结构

### 3.1 ListHaServersResponse

| 字段号 | 字段 | 类型 | 一定返回 | 说明 | 示例 |
| --- | --- | --- | --- | --- | --- |
| 1 | `code` | `HaServerListCode` 枚举 | 是 | 业务结果，取值见 3.3 | `HA_SERVER_LIST_SUCCESS` |
| 2 | `errmsg` | string | 是 | 成功时为 `success`，失败时为 `service discovery unavailable` | `success` |
| 3 | `servers` | repeated `HaServerInfo` | 是 | 存活实例列表，结构见 3.2。没有实例或失败时为空 | 见样例 |
| 4 | `ips` | repeated string | 是 | 所有实例 IP 去重后按字符串升序排列。没有实例或失败时为空 | `["127.0.0.1", "::1"]` |

### 3.2 HaServerInfo

| 字段号 | 字段 | 类型 | 一定返回 | 说明 | 示例 |
| --- | --- | --- | --- | --- | --- |
| 1 | `role` | string | 是 | 角色，取值为 `admin`、`analysis` 或 `receiver` | `analysis` |
| 2 | `id` | string | 是 | 注册信息的 `id` 字段，是进程启动时生成的 UUID。正常注册时与 etcd key 的最后一段相同，但接口不校验这一点 | `8a7b6c5d-4e3f-4a1b-9c0d-abcdef012345` |
| 3 | `ips` | repeated string | 是 | 实例上报的 IP，已去掉空串，按字符串升序排列，至少一个元素。实例内不去重。来源见表后说明 | `["127.0.0.1", "::1"]` |
| 4 | `startTime` | string | 是 | 进程启动时间，按 Asia/Shanghai 时区格式化，格式为 `2006-01-02T15:04:05+08:00`。零值时为 `""` | `2026-11-04T14:00:00+08:00` |
| 5 | `updatedAt` | string | 是 | 注册信息最后一次刷新的时间，格式同上。各进程按自己配置的 `discovery.serviceTimerInterval` 刷新，默认 3 秒 | `2026-11-04T14:30:00+08:00` |
| 6 | `uptime` | string | 是 | 实例自己上报的运行时长，原样透传。由 durafmt 生成，含多个单位并精确到微秒，只供人读，不要解析 | `6 seconds 8 milliseconds 437 microseconds` |

`ips` 由各进程启动时调用 `machine.GetLocalIPs()` 探测一次，之后不再更新。
只取物理网卡上的地址，并排除环回、链路本地、组播和未指定地址，所以真实结果中不会出现 `127.0.0.1` 或 `::1`。
本文档表格和样例中的环回地址只是示意值。

### 3.3 HaServerListCode

| 名称 | 值 | 含义 |
| --- | --- | --- |
| `HA_SERVER_LIST_SUCCESS` | 0 | 成功 |
| `HA_SERVER_LIST_FAIL` | 1 | 失败，discovery 不可用 |

### 3.4 proto 定义

摘自 [pkg/proto/idl/admin.proto](../../../pkg/proto/idl/admin.proto)：

```protobuf
// HaServerInfo one live HA server instance registered in etcd
message HaServerInfo {
    string          role      = 1;  // admin | analysis | receiver
    string          id        = 2;
    repeated string ips       = 3;
    string          startTime = 4;  // 2006-01-02T15:04:05-07:00, Asia/Shanghai
    string          updatedAt = 5;  // 2006-01-02T15:04:05-07:00, Asia/Shanghai
    string          uptime    = 6;
}

message ListHaServersRequest {}

// HaServerListCode result code for ListHaServers: success / failure
enum HaServerListCode {
    HA_SERVER_LIST_SUCCESS = 0;  // success
    HA_SERVER_LIST_FAIL    = 1;  // failure
}

message ListHaServersResponse {
    HaServerListCode      code    = 1;
    string                errmsg  = 2;
    repeated HaServerInfo servers = 3;
    repeated string       ips     = 4;
}

service AdminService {
    rpc ListHaServers(ListHaServersRequest) returns (ListHaServersResponse) {};
}
```

`AdminService` 中的其他方法（`Heartbeat`、`GetProbeConfig`）在上面省略。

### 返回 JSON 样例

样例为 protojson 形式，并输出默认值（对应 `protojson.MarshalOptions{EmitUnpopulated: true}`）：
字段名为 camelCase，枚举输出为名称。

**默认值省略规则**：不输出默认值时，值为 0 的枚举（`HA_SERVER_LIST_SUCCESS`）和空数组都会被省略。
这只影响 JSON 展示；用生成代码直接调用时，这些字段读到的就是默认值。

下面的样例中 `uptime` 为 `30 minutes`、IP 为环回地址，都是示意值；真实值见 3.2 节。

成功，有数据（gRPC 状态 OK）：

```json
{
  "code": "HA_SERVER_LIST_SUCCESS",
  "errmsg": "success",
  "servers": [
    {
      "role": "admin",
      "id": "6f1c2a3e-1b2d-4c5e-8f90-123456789abc",
      "ips": ["127.0.0.1"],
      "startTime": "2026-11-04T14:00:00+08:00",
      "updatedAt": "2026-11-04T14:30:00+08:00",
      "uptime": "30 minutes"
    },
    {
      "role": "analysis",
      "id": "8a7b6c5d-4e3f-4a1b-9c0d-abcdef012345",
      "ips": ["127.0.0.1", "::1"],
      "startTime": "2026-11-04T14:00:00+08:00",
      "updatedAt": "2026-11-04T14:30:00+08:00",
      "uptime": "30 minutes"
    },
    {
      "role": "receiver",
      "id": "c3d4e5f6-7a8b-4c9d-8e1f-0a1b2c3d4e5f",
      "ips": ["::1"],
      "startTime": "2026-11-04T14:00:00+08:00",
      "updatedAt": "2026-11-04T14:30:00+08:00",
      "uptime": "30 minutes"
    }
  ],
  "ips": ["127.0.0.1", "::1"]
}
```

成功，无数据（gRPC 状态 OK）：

```json
{
  "code": "HA_SERVER_LIST_SUCCESS",
  "errmsg": "success",
  "servers": [],
  "ips": []
}
```

失败（gRPC 状态 OK）：

```json
{
  "code": "HA_SERVER_LIST_FAIL",
  "errmsg": "service discovery unavailable",
  "servers": [],
  "ips": []
}
```

## 4. 错误码

| 场景 | gRPC 状态 | 业务码 | errmsg | 调用方处理建议 |
| --- | --- | --- | --- | --- |
| 成功 | OK | `HA_SERVER_LIST_SUCCESS` | `success` | 读取 `servers` 和 `ips` |
| discovery 不可用：etcd 不可达、读取超时、discovery 槽为空、任一角色前缀读取失败 | OK | `HA_SERVER_LIST_FAIL` | `service discovery unavailable` | 稍后重试，不要把空列表当作“没有实例” |
| 连不上 Admin | `Unavailable` | 无 | 无 | 检查地址和进程状态；这是传输层错误，不由本接口产生 |
| 调用方 deadline 到期 | `DeadlineExceeded`（客户端侧） | 无 | 无 | 调大 deadline，建议大于服务端超时 |
| 连到不支持该方法的旧版 Admin | `Unimplemented` | 无 | 无 | 升级 Admin |

- 业务失败时 gRPC 状态仍为 OK，调用方必须检查 `code`。
- etcd 的原始错误只写进日志，不会出现在 `errmsg` 里。
- 本接口不受 storage 状态影响，storage 重载期间也不会返回 `Unavailable`。
- etcd 恢复后接口会自动恢复，不需要重启 Admin。沙箱实测 mock etcd 重新启动约 7 秒后恢复。
  这是实测结果，不是服务承诺。
- 调用方 deadline 早于服务端超时到期时，客户端收到 `DeadlineExceeded`；服务端此时返回的是
  `HA_SERVER_LIST_FAIL` 业务响应，日志 `errmsg` 为 `context canceled`，指标中按 `grpc_code="OK"` 计数。

## 5. 调用示例

### 5.1 grpcurl

Admin 没有开启 reflection，需要通过 `-import-path` 和 `-proto` 指定 proto 文件，在 dbha-v2 根目录执行。
命令使用默认端口 50051，执行前把主机换成实际监听 host：

```bash
grpcurl -plaintext -emit-defaults -import-path pkg/proto/idl -proto admin.proto \
  -d '{}' 127.0.0.1:50051 AdminService/ListHaServers
```

> grpcurl 本身未实测（验证环境没有安装 grpcurl）。第 3 节的 protojson 样例已用 Go 客户端实测：
> 以 `protojson` 加 `EmitUnpopulated` 序列化真实响应，字段名、枚举名和空数组的输出与样例一致；
> 不开启 `EmitUnpopulated` 时，成功响应省略 `code`，失败响应省略 `servers` 和 `ips`，与“默认值省略规则”一致。

## 6. 行为说明

### 6.1 存活语义

- 各进程把注册信息写在 `/dbha/registry/{role}/self/{id}`，绑定 etcd 租约，TTL 为 6 秒。
  进程异常退出后，最多约 6 秒内仍会出现在列表里。
- `updatedAt` 默认每 3 秒刷新一次，可以用来判断记录是否过时。
- 处理请求的 Admin 自己也注册在 `admin/self` 下，所以结果里通常包含它自身，IP 为该进程探测到的本机地址。
  进程探测不到本机 IP 时，这条记录因 `ips` 为空被跳过。

### 6.2 排序与去重

- 实例先按角色 admin、analysis、receiver 排序，同角色再按 `id` 的字符串升序排序。
- 实例内的 `ips` 按字符串升序排列，不去重；顶层 `ips` 去重后按字符串升序排列。
- 排序是逐字符比较的字典序，不是按数值或地址族排序。例如两个只有末段不同的 IPv4 地址，末段为 `10` 的排在末段为 `2` 的前面；
  `127.0.0.1` 排在 `::1` 前面，因为字符 `1` 小于 `:`。

### 6.3 时间格式

时间统一按 `+08:00` 输出。运行环境缺少 tzdata 时，回退到固定的 UTC+8 时区，输出格式不变。

### 6.4 一致性与负载

- 三个角色前缀分三次读取，不是同一个 etcd revision 的快照。
- 没有缓存，每次请求都直接读 etcd。调用方不要高频轮询。

### 6.5 失败语义

任一前缀读取失败、discovery 槽为空或请求超时，整次请求失败，不返回部分结果。
失败响应中 `servers` 和 `ips` 都为空。
etcd 不可达时，调用会一直等到服务端超时（默认 3 秒）才返回 `HA_SERVER_LIST_FAIL`，
日志中的 `errmsg` 为 `context deadline exceeded`。调用方的 deadline 应大于服务端超时，否则会先收到 `DeadlineExceeded`，
此时服务端日志的 `errmsg` 为 `context canceled`。

### 6.6 热重载

- discovery 重载期间，请求只会返回成功或失败，不会出现其他状态。
- storage 重载或 MySQL 不可用时，本接口照常返回。

## 7. 可观测性

### 7.1 指标

指标从 APM 的 `/metrics` 读取，默认端口为 50080。下表指标名省略前缀 `dbha_v2_admin_`，
前缀和查询写法见 [admin 指标](../../observability/admin-metrics.md)。

| 指标 | 标签 | 说明 |
| --- | --- | --- |
| `grpc_requests_total` | `method`, `grpc_code` | 每次调用计数，`method` 为 `ListHaServers` |
| `grpc_request_duration_ms` | `method` | 调用耗时 |
| `grpc_request_size_bytes` | `method` | 请求大小 |
| `grpc_response_size_bytes` | `method` | 响应大小 |
| `grpc_request_errors_total` | `method` | gRPC 状态非 OK 时计数 |

业务失败时 gRPC 状态仍为 OK，所以 `grpc_code` 为 `OK`，也不计入 `grpc_request_errors_total`。
调用方 deadline 到期的调用也是如此：客户端收到 `DeadlineExceeded`，但服务端处理函数返回的是业务失败响应，
指标仍按 `grpc_code="OK"` 计数，不会出现 `grpc_code="DeadlineExceeded"`。
要发现业务失败，可以看 Admin 日志中的 `list ha servers failed`。

查看本接口的指标（主机同样需要换成 `apm.listenAddress` 的实际 host）：

```bash
curl -s http://127.0.0.1:50080/metrics | grep 'ListHaServers'
```

### 7.2 日志

| 关键字 | 级别 | 含义 |
| --- | --- | --- |
| `list ha servers failed, errmsg: ...` | Warn | 本次调用失败，`errmsg` 为 etcd 或 discovery 的原始错误 |

日志里不打印注册信息的 value。

## 8. 源码索引

| 内容 | 文件 |
| --- | --- |
| proto 定义 | [pkg/proto/idl/admin.proto](../../../pkg/proto/idl/admin.proto) |
| gRPC 方法与存储拦截器放行 | [internal/admin/grpc.go](../../../internal/admin/grpc.go) |
| 接入 discovery 槽与响应构造 | [internal/admin/haserver.go](../../../internal/admin/haserver.go) |
| 列举、过滤与排序 | [pkg/discovery/server_list.go](../../../pkg/discovery/server_list.go) |
| 时间格式 | [internal/admin/api/open/serializer/haserver.go](../../../internal/admin/api/open/serializer/haserver.go) |
| gRPC 指标拦截器 | [internal/admin/apm/grpc_interceptor.go](../../../internal/admin/apm/grpc_interceptor.go) |

---

返回：[接口文档索引](../README.md)
