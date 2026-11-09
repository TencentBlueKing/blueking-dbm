# Admin 指标与 Grafana 配置

本文汇总 admin 暴露的 Prometheus 指标，并给出 Grafana 抓取与看板配置。同系列文档：
[analysis 指标](analysis-metrics.md)、[receiver 指标](receiver-metrics.md)。

## 1. 暴露方式

- 监听地址取自 `admin.yaml` 的 `apm.listenAddress`，指标路径为 `/metrics`，同端口提供 `/health`。
  实现见 [pkg/haapm/server.go](../../pkg/haapm/server.go)。
- 示例地址取自 [etc/dbha-v2.server.rc.example](../../etc/dbha-v2.server.rc.example) 的
  `ADMIN_APM_LISTEN_ADDRESS`，为 `127.0.0.1:50080`。该变量为空时，渲染脚本会改用本机自动检测的 IPv4。
- 下文指标名统一省略前缀 `dbha_v2_admin_`。

> 代码里的 Subsystem 为 `dbha-v2-admin`（[internal/admin/resources.go](../../internal/admin/resources.go)），
> haapm 原样传给 client_golang（v1.23.2），可以正常注册。`/metrics` 默认把名称里的 `-` 转义为 `_`，输出
> `dbha_v2_admin_*`，本文查询按此书写。抓取方在 `Accept` 中声明 `escaping=allow-utf-8` 时会输出原始名称，
> 形如 `{"dbha-v2-admin_api_requests_total",...}`，此时本文查询匹配不到。

`/metrics` 还会带上 Prometheus 客户端默认的 `go_*`、`process_*`，不属于 admin 业务指标，下表不列。
Histogram 在抓取结果里展开为 `_bucket`、`_sum`、`_count`，下表写基础名。

## 2. 指标清单

业务指标共 18 个，定义见 [internal/admin/apm/metric.go](../../internal/admin/apm/metric.go)。

| 分组 | 指标名 | 类型 | 标签 | 含义 |
| --- | --- | --- | --- | --- |
| 服务 | `dbha_startup_time_sec` | Gauge | `service_id`, `service_name` | 进程启动的 Unix 时间，单位秒；help 写作运行时长，与实际值不符 |
| HTTP | `api_requests_total` | Counter | `method`, `path`, `status` | HTTP 请求累计数 |
| HTTP | `api_request_duration_ms` | Histogram | `method`, `path` | HTTP 耗时，单位 ms |
| HTTP | `api_request_size_bytes` | Histogram | `method`, `path` | 请求大小，单位字节 |
| HTTP | `api_response_size_bytes` | Histogram | `method`, `path` | 响应大小，单位字节 |
| HTTP | `api_request_errors_total` | Counter | `method`, `path` | HTTP 状态码大于等于 400 的累计数 |
| 元数据 | `probe_metadata_fallback_total` | Counter | `reason` | 本地缓存不可用、回退 DBM 的次数 |
| 热加载 | `config_reload_success` | Gauge | 无 | 最近一次 reload 无失败为 1，否则为 0 |
| 热加载 | `config_reload_failure` | Gauge | 无 | 最近一次 reload 有失败为 1，否则为 0 |
| 热加载 | `config_reload_duration_ms` | Gauge | 无 | 最近一次 reload 耗时，单位 ms |
| 热加载 | `config_reload_slot_count` | Gauge | `result` | 最近一次 reload 处理的资源槽数 |
| 热加载 | `config_reload_last_success_unix` | Gauge | 无 | 最近一次无失败 reload 的 Unix 时间 |
| gRPC | `grpc_requests_total` | Counter | `method`, `grpc_code` | gRPC 请求累计数，含成功和失败 |
| gRPC | `grpc_request_duration_ms` | Histogram | `method` | gRPC 耗时，单位 ms |
| gRPC | `grpc_request_size_bytes` | Histogram | `method` | gRPC 请求大小，单位字节 |
| gRPC | `grpc_response_size_bytes` | Histogram | `method` | gRPC 响应大小，单位字节 |
| gRPC | `grpc_request_errors_total` | Counter | `method` | 非 OK 状态累计数 |
| gRPC | `grpc_probe_config_result_total` | Counter | `code` | `GetProbeConfig` 业务结果累计数，仅在 gRPC 调用无错误时计数 |

有限标签取值：

| 标签 | 取值 |
| --- | --- |
| `reason` | `miss`、`stale` |
| `result` | `success`、`failure` |
| gRPC `method` | `Heartbeat`、`GetProbeConfig`、`ListHaServers`，其余记为 `unknown` |
| `grpc_code` | gRPC 标准状态码名称，例如 `OK`、`Unavailable`；无法识别时为 `unknown` |
| `code` | `SUCCESS`、`FAIL`、`NO_DATA`、`unknown` |

HTTP 指标不统计 `/health`、`/metrics` 和 swagger 路径，实现见
[internal/admin/apm/middleware.go](../../internal/admin/apm/middleware.go)。`path` 优先使用路由模板，未匹配路由时会落到
原始 URL，基数可能升高。

## 3. Prometheus 抓取配置

`targets` 只写 `host:port`，不要带 rc 里的 `http://`。

```yaml
scrape_configs:
  - job_name: dbha-admin
    metrics_path: /metrics
    scrape_interval: 15s
    static_configs:
      - targets:
          - 127.0.0.1:50080
```

## 4. Grafana 变量

| 变量 | 类型 | 配置 |
| --- | --- | --- |
| `method` | Query | `label_values(dbha_v2_admin_grpc_requests_total, method)`，勾选 Multi-value 与 Include All，Custom all value 留空 |
| `path` | Query | `label_values(dbha_v2_admin_api_requests_total, path)`，勾选 Multi-value 与 Include All，Custom all value 留空 |
| `rate_window` | Custom | `1m,5m,15m`，默认 `5m`，只允许单选 |

- 筛选变量在查询里统一写成 `=~"$var"`。Prometheus 数据源会对多选值做正则转义并拼成 `(a|b)`。
  不要写成 `${var:regex}`：它会把 `/` 转义成 `\/`，PromQL 解析时报 `unknown escape sequence`。
- Custom all value 留空，选 All 时只展开成实际存在的取值。写成 `.*` 会同时匹配空串，把启动时生成的空标签零值序列带进查询。
- `rate_window` 不能开启 Multi-value，否则 `[$rate_window]` 会变成非法区间。
- 时间窗变量统一命名为 `rate_window`，避免与 Grafana 内置的 `$__interval` 混淆。

## 5. 看板面板

查询中的 `$变量名`（如 `$rate_window`）是 Grafana 变量，需先按第 4 节建好变量再粘贴到面板。
在 Prometheus 页面直接执行时，把 `=~"$变量名"` 中的变量替换为 `.+`，把 `$rate_window` 换成具体时间窗，例如 `5m`。
`.+` 只匹配非空取值，替换后语法不变，仍会排除空标签零值序列。

多实例部署时，聚合都在原有 `by` 标签后追加 `instance`。热加载指标没有标签，按 `instance` 区分各个 admin。

| 行 | 面板 | 图形 | PromQL |
| --- | --- | --- | --- |
| 服务 | 实例存活 | Stat | `up{job="dbha-admin"}` |
| 服务 | 启动时间 | Stat | `max by (instance) (dbha_v2_admin_dbha_startup_time_sec) * 1000` |
| HTTP | 请求速率 | Time series | `sum by (instance, method, path) (rate(dbha_v2_admin_api_requests_total{path=~"$path"}[$rate_window]))` |
| HTTP | 错误速率 | Time series | `sum by (instance, method, path) (rate(dbha_v2_admin_api_request_errors_total{path=~"$path"}[$rate_window]))` |
| HTTP | P95 耗时 | Time series | `histogram_quantile(0.95, sum by (le, instance, path) (rate(dbha_v2_admin_api_request_duration_ms_bucket{path=~"$path"}[$rate_window])))` |
| gRPC | 请求速率 | Time series | `sum by (instance, method, grpc_code) (rate(dbha_v2_admin_grpc_requests_total{method=~"$method"}[$rate_window]))` |
| gRPC | 错误速率 | Time series | `sum by (instance, method) (rate(dbha_v2_admin_grpc_request_errors_total{method=~"$method"}[$rate_window]))` |
| gRPC | P95 耗时 | Time series | `histogram_quantile(0.95, sum by (le, instance, method) (rate(dbha_v2_admin_grpc_request_duration_ms_bucket{method=~"$method"}[$rate_window])))` |
| gRPC | 配置结果速率 | Time series | `sum by (instance, code) (rate(dbha_v2_admin_grpc_probe_config_result_total{code!=""}[$rate_window]))` |
| 元数据 | 缓存回退速率 | Time series | `sum by (instance, reason) (rate(dbha_v2_admin_probe_metadata_fallback_total{reason!=""}[$rate_window]))` |
| 热加载 | 最近一次是否成功 | Stat | `max by (instance) (dbha_v2_admin_config_reload_success)` |
| 热加载 | 最近一次耗时 | Stat | `max by (instance) (dbha_v2_admin_config_reload_duration_ms)` |
| 热加载 | 资源槽结果 | Stat | `sum by (instance, result) (dbha_v2_admin_config_reload_slot_count{result!=""})` |
| 热加载 | 最近成功时间 | Stat | `max by (instance) (dbha_v2_admin_config_reload_last_success_unix) * 1000` |

- 时间戳面板的单位选 `From Now`（日期时间），乘以 1000 是因为 Grafana 按毫秒解释时间戳。
- 进程从未完成过一次 reload 时，热加载 Gauge 为 0，不代表失败。
- 进程启动时，每个带标签的指标会预先生成一条标签全为空、值为 0 的序列。没有其他筛选条件的分组面板，用 `!=""` 排除这条序列。
- 缓存回退速率持续升高，说明 admin 正把 probe 的周期性请求放大到 DBM，应检查元数据同步延迟。

## 6. 基数说明

`path` 在未匹配路由时会带上原始 URL，只用于排障明细面板。gRPC 的 `method`、`grpc_code`、`code` 都是有限集合，可以放心用于总览分组。

---

返回：[文档入口](../README.md)
