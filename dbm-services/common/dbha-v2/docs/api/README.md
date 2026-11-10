# Admin 接口文档

本目录说明 Admin 对外提供的接口。内容以 dbha-v2 的实际实现为准。

## 1. 目录说明

- HTTP 接口放在 [http/](http/)，gRPC 接口放在 [grpc/](grpc/)，每个接口一个文件。
- 每个接口文件都能独立阅读，基本信息、行为说明和错误码在文件内完整写出。
- 文件命名规则：
  - **HTTP**：路径去掉公共前缀 `/api/admin/`，再把 `/` 换成 `-`。
    例如 `/api/admin/meta/ha-servers` 对应 `meta-ha-servers.md`。
  - **gRPC**：方法名的 kebab-case 形式。例如 `ListHaServers` 对应 `list-ha-servers.md`。
- 新增接口时按同样规则放进对应子目录，并在下面的接口清单里加一行。

## 2. 接口清单

### HTTP

| 方法 | 路径 | 说明 | 文档 |
| --- | --- | --- | --- |
| `GET` | `/api/admin/meta/ha-servers` | 列出存活的 HA Server 实例及其 IP | [meta-ha-servers.md](http/meta-ha-servers.md) |

### gRPC

| 服务和方法 | 说明 | 文档 |
| --- | --- | --- |
| `AdminService/ListHaServers` | 列出存活的 HA Server 实例及其 IP | [list-ha-servers.md](grpc/list-ha-servers.md) |

## 3. 服务地址

### 3.1 默认地址

Admin 代码不给监听地址设默认值。默认地址由部署时的渲染脚本
[scripts/render_configs.py](../../scripts/render_configs.py) 生成，写入 `admin.yaml`：

| 服务 | 配置项 | rc 变量 | rc 变量为空时的默认值 |
| --- | --- | --- | --- |
| Web（HTTP 接口） | `web.listenAddress` | `ADMIN_WEB_LISTEN_ADDRESS` | `http://<本机 IPv4>:50060` |
| gRPC | `grpc.listenAddress` | `ADMIN_GRPC_LISTEN_ADDRESS` | `<本机 IPv4>:50051` |
| APM（`/metrics`） | `apm.listenAddress` | `ADMIN_APM_LISTEN_ADDRESS` | `http://<本机 IPv4>:50080` |

- 默认端口来自 `render_configs.py` 中的 `_DEFAULT_ADMIN_WEB_LISTEN_PORT=50060`、
  `_DEFAULT_ADMIN_GRPC_LISTEN_PORT=50051`、`_DEFAULT_ADMIN_APM_LISTEN_PORT=50080`，
  与 [etc/dbha-v2.server.rc.example](../../etc/dbha-v2.server.rc.example) 的注释一致。
- `<本机 IPv4>` 是渲染脚本自动探测的本机主 IPv4。三个 rc 变量只写 `:<port>` 时，主机部分同样自动探测，
  端口取 rc 中的值。
- `web.listenAddress` 写成 `host:port` 或 `http://host:port` 都可以，不写 scheme 时按 http 处理。

### 3.2 示例里的地址

文档示例统一使用默认端口，主机写 `127.0.0.1`：Web 为 `127.0.0.1:50060`，gRPC 为 `127.0.0.1:50051`，
APM 为 `127.0.0.1:50080`。

> **注意**：rc 变量为空、按默认渲染部署时，Admin 监听在探测到的本机 IPv4 上，而不是 `127.0.0.1`，
> 照抄示例会连接被拒绝。执行前要把示例中的 `127.0.0.1` 换成 `admin.yaml` 里实际的监听 host；
> 端口改过的话，也以配置为准。

`etc/dbha-v2.server.rc.example` 里 gRPC 和 APM 显式写了 `127.0.0.1:50051`、`http://127.0.0.1:50080`，
只有 Web 留空。照搬这个示例部署时，gRPC 和 APM 监听 `127.0.0.1`，Web 监听本机 IPv4 的 50060 端口。
所以三个服务的 host 要分别以 `admin.yaml` 为准。

### 3.3 鉴权

Admin Web 没有启用鉴权：`hanet` 提供了 `SetAuthHandler`，但 Admin 没有调用。gRPC 也没有鉴权。

### 3.4 平台接入

dbm 平台通过 `HADBApiV2`（`dbm-ui/backend/components/hadbv2/client.py`）访问 dbha-v2 的 HTTP 接口，
基地址为 `HADBV2_APIGW_DOMAIN`（默认 `http://bk-dbm-hadb-api`）。
`HADBApiV2` 目前只注册了 `switchqueue/` 和 `switchlogs/`，没有 HA Server 列表接口，所以 dbm 平台还没有调用它的代码。
网关的路由配置不在本仓库中，无法从仓库确认网关是否已转发该路径；需要调用时可以直连 Admin 的 Web 端口。

## 4. HTTP 公共约定（V1 兼容接口）

Admin 的 HTTP 接口有两套响应格式，本节只描述 V1 兼容格式。

| 格式 | 使用的接口 | 说明 |
| --- | --- | --- |
| V1 兼容格式 | `/api/admin/meta/ha-servers`、`/api/admin/switchqueue/`、`/api/admin/switchlogs/`、`/api/admin/switchqueue/autofix/` | 见 4.1 至 4.3 |
| REST 格式 | `/api/admin/strategies/...`、`/api/admin/global/strategies/...` | 见 4.4，本目录暂未收录这些接口的文档 |

### 4.1 响应结构

V1 兼容接口返回下面的结构，字段顺序固定为 `data`、`code`、`message`，
对应 [internal/admin/ginx/response.go](../../internal/admin/ginx/response.go) 中的 `V1ResponseInfo`：

```json
{
  "data": {},
  "code": 0,
  "message": ""
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `data` | 由接口决定 | 成功时为业务数据；失败时为空字符串 `""` |
| `code` | int | 业务码：`0` 表示成功（`RespOK`），`1` 表示失败（`RespErr`） |
| `message` | string | 成功时一般为 `""`；失败时为错误说明 |

- 响应头为 `Content-Type: application/json; charset=utf-8`。
- V1 兼容接口的业务码目前只有 `0` 和 `1` 两个值，没有细分错误码。

### 4.2 状态码

| 情况 | HTTP 状态码 | 响应体 |
| --- | --- | --- |
| 成功 | 200 | V1 结构，`code=0` |
| 业务失败 | 400 | V1 结构，`code=1`，`data=""` |
| storage 资源不可用 | 503 | 空。声明不依赖 storage 的接口除外；未注册的路径同样返回 503 |
| 未注册的路径、不支持的方法 | 404 | gin 默认的纯文本 `404 page not found`，不是 JSON |
| 路径末尾多一个或少一个 `/` | GET 为 301，其他方法为 307 | 重定向到已注册的路径，响应体没有业务含义 |

- “storage 资源不可用”指 storage 资源槽为空，或当前 storage 资源正在关闭（storage 重载换代时旧资源退役），
  对应 [internal/admin/resources.go](../../internal/admin/resources.go) 中 `storageSlot.Get()` 为空或 `acquire()` 失败。
- Admin 运行中 MySQL 断开不属于这种情况，不会返回 503：沙箱实测此时 `GET /api/admin/strategies/` 返回 400。
- 不支持的方法返回 404 而不是 405，因为 gin 的 `HandleMethodNotAllowed` 为 `false`。
- 末尾 `/` 的重定向由 gin 的 `RedirectTrailingSlash` 处理，只在同一方法下存在对应路径时发生。
  例如 `/api/admin/switchqueue/` 注册时带 `/`，`POST /api/admin/switchqueue` 会得到 307。
- 未注册的路径、不支持的方法和末尾 `/` 重定向这三种情况，不属于 V1 和 REST 中的任何一种格式。

### 4.3 与 dbm 错误码惯例的差异

- dbha-v2 的 V1 兼容接口业务失败时返回 HTTP 400。dbm 其他 Go 服务（db-priv、db-partition、db-resource 等）
  固定返回 HTTP 200，并使用 `go-pubpkg/errno` 中的错误码，这与 dbha-v2 不同。
- dbha-v2 的内部错误码（`pkg/gerrors`）只出现在进程内部和日志中，不会写进 HTTP 响应。
- dbm 平台的 `BaseApi`（`dbm-ui/backend/components/base.py`）遇到非 200 状态码时，不会把响应体当作 JSON 解析：
  - `_send_request` 先抛出 `DataAPIException`，消息格式为
    `[<模块名>]API请求异常：([<状态码>]<响应体原文>) path => <路径>`。
    响应体为空时用状态码的原因短语代替，例如 503 时为 `Service Unavailable`。
  - `__call__` 捕获后，再包装成 `ApiRequestError`（`ERROR_CODE` 为 `015`）抛给调用方。
  - 例如本接口返回 400 时，消息中包含
    `([400]{"data":"","code":1,"message":"service discovery unavailable"})`。
    调用方拿不到结构化的 `code` 和 `message`，只能自己解析这段文本。
  - 平台现有的 `switchqueue/`、`switchlogs/` 调用同样如此。
- 调用方建议按以下顺序处理：
  1. 先看 HTTP 状态码。
  2. 200 时再看 `code`。
  3. 400 时读响应体中的 `message`。
  4. 301、307、404、503 时响应体没有业务含义。

### 4.4 REST 格式（参考）

`strategies` 相关接口使用 REST 格式，与 V1 兼容格式不同，这里只列出结构，便于区分：

- 查询成功返回 200，响应体为 `{"data": ...}`；创建成功返回 201，响应体为 `null`；
  更新、删除、修改状态成功返回 204，没有响应体。
- 失败时响应体为 `{"error": {"code": "...", "message": "..."}}`，`error.code` 是字符串，
  HTTP 状态码随错误类型变化：

  | `error.code` | HTTP 状态码 |
  | --- | --- |
  | `BadRequest` | 400 |
  | `NotFound` | 404 |
  | `InternalServerError` | 500，`message` 以 `system error: ` 开头 |

结构定义见 [internal/admin/ginx/response.go](../../internal/admin/ginx/response.go) 中的
`SuccessResponse`、`ErrorResponse`。

## 5. gRPC 公共约定

- proto 文件：[pkg/proto/idl/admin.proto](../../pkg/proto/idl/admin.proto)。
- 单条消息的收发上限由 `grpc.maxReceiveMessageSize`、`grpc.maxSendMessageSize` 配置
  （rc 变量为 `ADMIN_GRPC_MAX_RECEIVE_MESSAGE_SIZE`、`ADMIN_GRPC_MAX_SEND_MESSAGE_SIZE`），默认均为 10 MiB。
- 业务结果通过响应里的 `code` 字段表达。gRPC 状态为 OK 不代表业务成功，调用方必须检查 `code`。
- 调试工具：
  - Admin 没有开启 reflection，用 grpcurl 调用时需要加 `-import-path pkg/proto/idl -proto admin.proto`。
  - 加 `-emit-defaults` 可以输出值为默认值的字段。grpcurl 未在验证环境实测。
  - 沙箱里可以改用 mock 客户端 `build/dbha-ha-sandbox-mock`（用 `make ha-sandbox-mock` 构建）。
    同时传 `--admin-grpc-addr` 和 `--admin-web-addr` 时，它会分别调用 gRPC 和 HTTP 并比对结果；
    只传一个时只调用对应的协议。

## 6. 文档模板

新增接口文档时按下面的章节骨架书写：

````markdown
# <接口中文名>

<一句话说明用途和结果范围>

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| 协议 | HTTP / gRPC |
| 地址 | HTTP：`http://<web.listenAddress><路径>`；gRPC：`<grpc.listenAddress>` |
| 方法 | HTTP：`GET` 等；gRPC：`<Service>/<Method>`（完整方法名 `/<Service>/<Method>`） |
| 依赖 | 依赖的外部组件，是否依赖 storage |
| 鉴权 | 有或无 |
| 超时 | 服务端超时及其配置项 |
| 引入版本 | issue 编号 |

## 2. 请求参数

| 位置 | 参数名 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |

HTTP 的“位置”列取 path、query、header、body；gRPC 用“字段号”代替。
没有参数时写一行“无”，并说明多传的参数会怎样处理。

### 请求 JSON 样例

请求体是 JSON 时，给出完整的格式化样例，所有字段都要出现（含可选字段），值用有意义的示例值。
请求体为空时明确写“无请求体”。gRPC 给出 grpcurl `-d` 使用的 JSON。

## 3. 返回结构

按层级每层一张表：

| 字段 | 类型 | 一定返回 | 说明 | 示例 |
| --- | --- | --- | --- | --- |

gRPC 的表额外加一列“字段号”，并附 proto 消息定义原文。

### 返回 JSON 样例

给出完整的格式化 JSON，每个字段都要出现，数组至少放能体现排序和去重规则的多个元素。
以下三种情况各一份：成功有数据、成功无数据、失败。gRPC 使用 protojson 形式，并注明默认值省略规则。

## 4. 错误码

| 场景 | HTTP 状态码 / gRPC 状态 | 业务码 | message / errmsg | 调用方处理建议 |
| --- | --- | --- | --- | --- |

## 5. 调用示例

只放可直接执行的命令和实测输出，不重复第 2、3 节的结构样例。成功和失败各一组。
JSON 输出格式化后给出，并注明原始输出为单行紧凑 JSON。没有实测的命令要明确标注“未实测”，不写其输出。

## 6. 行为说明

存活语义、排序与去重、时间格式、一致性与负载、失败语义、热重载期间的表现。

## 7. 可观测性

相关指标（含标签和错误计数规则）和日志关键字。

## 8. 源码索引

| 内容 | 文件 |
| --- | --- |
````

---

返回：[文档总入口](../README.md)
