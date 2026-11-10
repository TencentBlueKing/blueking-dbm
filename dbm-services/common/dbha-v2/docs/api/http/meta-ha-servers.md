# HA Server 列表（HTTP）

列出当前存活的 admin、analysis、receiver 实例，以及所有实例 IP 去重后的列表。
结果不包含 probe，只读取默认注册根 `/dbha/registry`，不支持自定义根路径。

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| 协议 | HTTP |
| 地址 | `http://<web.listenAddress>/api/admin/meta/ha-servers` |
| 方法 | `GET` |
| 依赖 | 只依赖 etcd，不依赖 storage（MySQL 不可用或 storage 重载期间也能调用） |
| 鉴权 | 无 |
| 超时 | `discovery.serviceUpdateTimeout`（rc 变量 `ADMIN_DISCOVERY_SERVICE_UPDATE_TIMEOUT`），见下方说明 |
| 引入版本 | issue #21530 |

- 默认端口为 50060，示例地址为 `http://127.0.0.1:50060/api/admin/meta/ha-servers`。
- **注意**：按默认渲染部署时，Admin Web 监听在探测到的本机 IPv4 上，而不是 `127.0.0.1`。
  执行示例前要把 `127.0.0.1` 换成 `admin.yaml` 中 `web.listenAddress` 的实际 host，端口也以配置为准。
  地址的来源见 [接口文档索引](../README.md#3-服务地址)。
- 超时：未配置或不大于 0 时为 3 秒。三个角色前缀共用这一个超时，超时后整次请求失败。

## 2. 请求参数

| 位置 | 参数名 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 无 | 无 | 无 | 无 | 无 | 不需要任何 path、query、header 或 body 参数 |

多传的 query 参数或请求体会被忽略，不报错，也不影响结果。

### 请求 JSON 样例

无请求体。

## 3. 返回结构

### 3.1 顶层

| 字段 | 类型 | 一定返回 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| `data` | object 或 string | 是 | 成功时为对象，结构见 3.2；失败时为空字符串 `""` | `{"servers": [], "ips": []}` |
| `code` | int | 是 | 业务码：`0` 表示成功，`1` 表示失败 | `0` |
| `message` | string | 是 | 成功时为 `""`；失败时为固定文案 `service discovery unavailable` | `""` |

### 3.2 data

| 字段 | 类型 | 一定返回 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| `servers` | array of object | 是 | 存活实例列表，结构见 3.3。没有实例时为 `[]`，不会是 `null` | `[]` |
| `ips` | array of string | 是 | 所有实例 IP 去重后按字符串升序排列。没有实例时为 `[]` | `["127.0.0.1", "::1"]` |

### 3.3 data.servers[]

| 字段 | 类型 | 一定返回 | 说明 | 示例 |
| --- | --- | --- | --- | --- |
| `role` | string | 是 | 角色，取值为 `admin`、`analysis` 或 `receiver` | `analysis` |
| `id` | string | 是 | 注册信息的 `id` 字段，是进程启动时生成的 UUID。正常注册时与 etcd key 的最后一段相同，但接口不校验这一点 | `8a7b6c5d-4e3f-4a1b-9c0d-abcdef012345` |
| `ips` | array of string | 是 | 实例上报的 IP，已去掉空串，按字符串升序排列，至少一个元素。实例内不去重。来源见表后说明 | `["127.0.0.1", "::1"]` |
| `start_time` | string | 是 | 进程启动时间，按 Asia/Shanghai 时区格式化，格式为 `2006-01-02T15:04:05+08:00`。零值时为 `""` | `2026-11-04T14:00:00+08:00` |
| `updated_at` | string | 是 | 注册信息最后一次刷新的时间，格式同上。各进程按自己配置的 `discovery.serviceTimerInterval` 刷新，默认 3 秒 | `2026-11-04T14:30:00+08:00` |
| `uptime` | string | 是 | 实例自己上报的运行时长，原样透传。由 durafmt 生成，含多个单位并精确到微秒，只供人读，不要解析 | `6 seconds 8 milliseconds 437 microseconds` |

`ips` 由各进程启动时调用 `machine.GetLocalIPs()` 探测一次，之后不再更新。
只取物理网卡上的地址，并排除环回、链路本地、组播和未指定地址，所以真实结果中不会出现 `127.0.0.1` 或 `::1`。
本文档表格和样例中的环回地址只是示意值。

### 返回 JSON 样例

实际响应是单行紧凑 JSON，字段顺序固定为 `data`、`code`、`message`。下面的样例经过格式化，只为方便阅读。
样例和第 5 节实测数据中的 `uptime` 为 `30 minutes`、IP 为环回地址，都是写入 mock etcd 的示意值；真实值见 3.3 节。

成功，有数据（HTTP 200）。analysis 有两个 IP，体现实例内排序；多个实例共用 IP，体现顶层去重：

```json
{
  "data": {
    "servers": [
      {
        "role": "admin",
        "id": "6f1c2a3e-1b2d-4c5e-8f90-123456789abc",
        "ips": ["127.0.0.1"],
        "start_time": "2026-11-04T14:00:00+08:00",
        "updated_at": "2026-11-04T14:30:00+08:00",
        "uptime": "30 minutes"
      },
      {
        "role": "analysis",
        "id": "8a7b6c5d-4e3f-4a1b-9c0d-abcdef012345",
        "ips": ["127.0.0.1", "::1"],
        "start_time": "2026-11-04T14:00:00+08:00",
        "updated_at": "2026-11-04T14:30:00+08:00",
        "uptime": "30 minutes"
      },
      {
        "role": "receiver",
        "id": "c3d4e5f6-7a8b-4c9d-8e1f-0a1b2c3d4e5f",
        "ips": ["::1"],
        "start_time": "2026-11-04T14:00:00+08:00",
        "updated_at": "2026-11-04T14:30:00+08:00",
        "uptime": "30 minutes"
      }
    ],
    "ips": ["127.0.0.1", "::1"]
  },
  "code": 0,
  "message": ""
}
```

成功，无数据（HTTP 200）：

```json
{
  "data": {
    "servers": [],
    "ips": []
  },
  "code": 0,
  "message": ""
}
```

失败（HTTP 400）：

```json
{
  "data": "",
  "code": 1,
  "message": "service discovery unavailable"
}
```

## 4. 错误码

| 场景 | HTTP 状态码 | 业务码 | message | 调用方处理建议 |
| --- | --- | --- | --- | --- |
| 成功 | 200 | `0` | `""` | 读取 `data` |
| discovery 不可用：etcd 不可达、读取超时、discovery 槽为空、任一角色前缀读取失败 | 400 | `1` | `service discovery unavailable`，`data` 为 `""` | 稍后重试，不要把它当作“没有实例” |
| GET 且路径末尾带 `/` | 301 | 无 | 无业务响应体 | 改用不带 `/` 的路径 |
| 非 GET 方法（POST、PUT、DELETE、PATCH、HEAD、OPTIONS），包括路径末尾带 `/` 时 | 404；storage 资源不可用时为 503 | 无 | 纯文本 `404 page not found`；503 时响应体为空 | 改用 GET |
| 路径不精确匹配（如 `/api/admin/meta/ha-server`、`/api/admin/meta/HA-SERVERS`，路径区分大小写） | 404；storage 资源不可用时为 503 | 无 | 同上 | 检查路径 |

- 失败时由 `V1ErrorJSONResponse` 返回 400（见 `internal/admin/ginx/response.go`），不会返回 503。
- etcd 的原始错误只写进日志，不会出现在响应里。
- etcd 恢复后接口会自动恢复，不需要重启 Admin。沙箱实测 mock etcd 重新启动约 7 秒后恢复。
  这是实测结果，不是服务承诺。
- 只有精确的 `GET /api/admin/meta/ha-servers` 跳过 storage 检查，所以其他方法和路径在 storage 资源不可用时返回 503。
  storage 资源不可用的含义见 [接口文档索引](../README.md#42-状态码)；Admin 运行中 MySQL 断开时本接口照常返回 200。

## 5. 调用示例

命令使用默认端口 50060，执行前把主机换成实际监听 host。下面的输出在沙箱中实测
（mock etcd 中写入与第 3 节样例相同的注册数据，并删除了 Admin 自身的注册记录），只有端口和 `Date` 头不同。

实际响应体是单行紧凑 JSON，下面为方便阅读做了格式化，字段、顺序和取值都与原始输出一致。
需要在终端里看到格式化结果时，可以在命令后接 `| python3 -m json.tool`。

查询列表：

```bash
curl -s http://127.0.0.1:50060/api/admin/meta/ha-servers
```

```json
{
  "data": {
    "servers": [
      {
        "role": "admin",
        "id": "6f1c2a3e-1b2d-4c5e-8f90-123456789abc",
        "ips": ["127.0.0.1"],
        "start_time": "2026-11-04T14:00:00+08:00",
        "updated_at": "2026-11-04T14:30:00+08:00",
        "uptime": "30 minutes"
      },
      {
        "role": "analysis",
        "id": "8a7b6c5d-4e3f-4a1b-9c0d-abcdef012345",
        "ips": ["127.0.0.1", "::1"],
        "start_time": "2026-11-04T14:00:00+08:00",
        "updated_at": "2026-11-04T14:30:00+08:00",
        "uptime": "30 minutes"
      },
      {
        "role": "receiver",
        "id": "c3d4e5f6-7a8b-4c9d-8e1f-0a1b2c3d4e5f",
        "ips": ["::1"],
        "start_time": "2026-11-04T14:00:00+08:00",
        "updated_at": "2026-11-04T14:30:00+08:00",
        "uptime": "30 minutes"
      }
    ],
    "ips": ["127.0.0.1", "::1"]
  },
  "code": 0,
  "message": ""
}
```

查看状态码和响应头：

```bash
curl -s -i http://127.0.0.1:50060/api/admin/meta/ha-servers
```

```text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Date: Mon, 09 Nov 2026 08:12:15 GMT
Content-Length: 631
```

响应头之后是空行和响应体，响应体与上一个示例相同。`Content-Length` 是单行紧凑 JSON 的字节数。

只取顶层 IP 列表，每行一个：

```bash
curl -s http://127.0.0.1:50060/api/admin/meta/ha-servers \
  | python3 -c 'import json,sys; print("\n".join(json.load(sys.stdin)["data"]["ips"]))'
```

```text
127.0.0.1
::1
```

失败：etcd 不可达时，请求等到服务端超时（默认 3 秒）后返回：

```bash
curl -s -i http://127.0.0.1:50060/api/admin/meta/ha-servers
```

```text
HTTP/1.1 400 Bad Request
Content-Type: application/json; charset=utf-8
Date: Mon, 09 Nov 2026 08:12:22 GMT
Content-Length: 62
```

响应体：

```json
{
  "data": "",
  "code": 1,
  "message": "service discovery unavailable"
}
```

Admin 日志中对应的告警，时间与上面的 `Date` 头一致（`08:12:22 GMT` 即 `16:12:22+0800`）。
`errmsg` 为原始错误，只出现在日志里。日志文件中每条是一行 JSON，下面做了格式化：

```json
{
  "level": "warn",
  "time": "2026-11-09T16:12:22.926+0800",
  "msg": "list ha servers failed, errmsg: context deadline exceeded"
}
```

路径末尾带 `/`：

```bash
curl -s -i http://127.0.0.1:50060/api/admin/meta/ha-servers/
```

```text
HTTP/1.1 301 Moved Permanently
Content-Type: text/html; charset=utf-8
Location: /api/admin/meta/ha-servers
Date: Mon, 09 Nov 2026 07:53:17 GMT
Content-Length: 61

<a href="/api/admin/meta/ha-servers">Moved Permanently</a>.
```

使用非 GET 方法：

```bash
curl -s -i -X POST http://127.0.0.1:50060/api/admin/meta/ha-servers
```

```text
HTTP/1.1 404 Not Found
Content-Type: text/plain
Date: Mon, 09 Nov 2026 07:53:17 GMT
Content-Length: 18

404 page not found
```

## 6. 行为说明

### 6.1 存活语义

- 各进程把注册信息写在 `/dbha/registry/{role}/self/{id}`，绑定 etcd 租约，TTL 为 6 秒。
  进程异常退出后，最多约 6 秒内仍会出现在列表里。
- `updated_at` 默认每 3 秒刷新一次，可以用来判断记录是否过时。
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
etcd 不可达时，请求会一直等到服务端超时（默认 3 秒）才返回 400，日志中的 `errmsg` 为 `context deadline exceeded`。

### 6.6 热重载

- discovery 重载期间，请求只会返回成功或失败，不会出现其他状态。
- storage 重载或 MySQL 不可用时，本接口照常返回。

## 7. 可观测性

### 7.1 指标

指标从 APM 的 `/metrics` 读取，默认端口为 50080。下表指标名省略前缀 `dbha_v2_admin_`，
前缀和查询写法见 [admin 指标](../../observability/admin-metrics.md)。

| 指标 | 标签 | 说明 |
| --- | --- | --- |
| `api_requests_total` | `method`, `path`, `status` | 每次请求计数，`path` 为 `/api/admin/meta/ha-servers` |
| `api_request_duration_ms` | `method`, `path` | 请求耗时 |
| `api_request_size_bytes` | `method`, `path` | 请求大小 |
| `api_response_size_bytes` | `method`, `path` | 响应大小 |
| `api_request_errors_total` | `method`, `path` | 状态码大于等于 400 时计数，业务失败返回 400 时也会计入 |

查看本接口的指标（主机同样需要换成 `apm.listenAddress` 的实际 host）：

```bash
curl -s http://127.0.0.1:50080/metrics | grep 'meta/ha-servers'
```

### 7.2 日志

| 关键字 | 级别 | 含义 |
| --- | --- | --- |
| `list ha servers failed, errmsg: ...` | Warn | 本次请求失败，`errmsg` 为 etcd 或 discovery 的原始错误 |

日志里不打印注册信息的 value。

## 8. 源码索引

| 内容 | 文件 |
| --- | --- |
| 路由注册 | [internal/admin/api/open/router.go](../../../internal/admin/api/open/router.go) |
| 请求处理 | [internal/admin/api/open/handler/haserver.go](../../../internal/admin/api/open/handler/haserver.go) |
| 返回结构与时间格式 | [internal/admin/api/open/serializer/haserver.go](../../../internal/admin/api/open/serializer/haserver.go) |
| V1 响应结构 | [internal/admin/ginx/response.go](../../../internal/admin/ginx/response.go) |
| 列举、过滤与排序 | [pkg/discovery/server_list.go](../../../pkg/discovery/server_list.go) |
| 接入 discovery 槽 | [internal/admin/haserver.go](../../../internal/admin/haserver.go) |
| 跳过 storage 检查 | [internal/admin/resources.go](../../../internal/admin/resources.go) 中的 `skipStorageForHTTP` |

---

返回：[接口文档索引](../README.md)
