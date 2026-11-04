# Analysis 指标与 Grafana 配置

本文汇总 analysis 暴露的 Prometheus 指标，并给出 Grafana 抓取与看板配置。同系列文档：
[admin 指标](admin-metrics.md)、[receiver 指标](receiver-metrics.md)。

## 1. 暴露方式

- 监听地址取自 `analysis.yaml` 的 `apm.listenAddress`，指标路径为 `/metrics`，同端口提供 `/health`。
  实现见 [pkg/haapm/server.go](../../pkg/haapm/server.go)。
- 示例地址取自 [etc/dbha-v2.server.rc.example](../../etc/dbha-v2.server.rc.example) 的
  `ANALYSIS_APM_LISTEN_ADDRESS`，为 `127.0.0.1:50082`。该变量为空时，渲染脚本会改用本机自动检测的 IPv4。
- 下文指标名统一省略前缀 `dbha_v2_analysis_`。

> 代码里的 Subsystem 为 `dbha-v2-analysis`（[internal/analysis/service.go](../../internal/analysis/service.go)），
> haapm 原样传给 client_golang（v1.23.2），可以正常注册。`/metrics` 默认把名称里的 `-` 转义为 `_`，输出
> `dbha_v2_analysis_*`，本文查询按此书写。抓取方在 `Accept` 中声明 `escaping=allow-utf-8` 时会输出原始名称，
> 形如 `{"dbha-v2-analysis_scan_business_total",...}`，此时本文查询匹配不到。

`/metrics` 还会带上 Prometheus 客户端默认的 `go_*`、`process_*`，不属于 analysis 业务指标，下表不列。
Histogram 在抓取结果里展开为 `_bucket`、`_sum`、`_count`，下表写基础名。

## 2. 指标清单

业务指标共 35 个：框架 28 个（含 `dbha_startup_time_sec`），MySQL 5 个，Redis 2 个。定义见
[internal/analysis/apm/metric.go](../../internal/analysis/apm/metric.go)、
[internal/provider/mysql/metrics/metrics.go](../../internal/provider/mysql/metrics/metrics.go)、
[internal/provider/redis/metrics/metrics.go](../../internal/provider/redis/metrics/metrics.go)。

| 分组 | 指标名 | 类型 | 标签 | 含义 |
| --- | --- | --- | --- | --- |
| 服务 | `dbha_startup_time_sec` | Gauge | `service_id`, `service_name` | 进程启动的 Unix 时间，单位秒；help 写作运行时长，与实际值不符 |
| 调度 | `am_business_total` | Gauge | `service_id`, `service_name` | 当前实例负责的业务数 |
| 调度 | `scan_business_total` | Counter | `service_id`, `service_name` | 扫描处理的业务累计数 |
| 调度 | `scan_business_time_consuming_ms` | Histogram | `service_id`, `service_name` | 一轮扫描耗时，单位 ms |
| 调度 | `pop_switch_business_total` | Counter | `service_id`, `service_name` | 出队切换处理的业务累计数 |
| 调度 | `pop_switch_time_consuming_ms` | Histogram | `service_id`, `service_name` | 单业务出队切换耗时，单位 ms |
| 调度 | `sliding_window_size` | Gauge | `service_id`, `service_name`, `biz_id` | 业务故障滑窗长度 |
| 切换 | `trigger_switching_instance_total` | Counter | `service_id`, `service_name` | 触发切换的实例累计数 |
| 切换 | `switching_instance_success_total` | Counter | `service_id`, `service_name` | 切换成功累计数 |
| 切换 | `switching_instance_error_total` | Counter | `service_id`, `service_name` | 切换失败累计数 |
| 切换 | `switching_time_consuming_ms` | Histogram | `db_type`, `service_id`, `service_name` | 整体切换耗时，单位 ms |
| MySQL | `mysql_cluster_switching_time_consuming_ms` | Histogram | `switch_id`, `action_scope`, `db_type` | 集群级切换耗时 |
| MySQL | `mysql_host_switching_time_consuming_ms` | Histogram | `switch_id`, `action_scope`, `db_type` | 主机级切换耗时 |
| MySQL | `mysql_instance_switching_time_consuming_ms` | Histogram | `switch_id`, `action_scope`, `db_type` | 实例级切换耗时 |
| MySQL | `mysql_switching_success_total` | Counter | `action_scope`, `db_type` | MySQL 切换成功累计数 |
| MySQL | `mysql_switching_error_total` | Counter | `action_scope`, `db_type` | MySQL 切换失败累计数 |
| Redis | `redis_switching_success_total` | Counter | `action_scope`, `db_type` | Redis 切换成功累计数，当前不会增长 |
| Redis | `redis_switching_error_total` | Counter | `action_scope`, `db_type` | Redis 切换失败累计数，当前不会增长 |
| 存储 | `db_query_time_consuming_ms` | Histogram | `query_type`, `service_id`, `service_name` | 数据库查询耗时 |
| 存储 | `db_query_error_total` | Counter | `query_type`, `service_id`, `service_name` | 数据库查询错误累计数 |
| 外部 API | `third_party_api_request_time_consuming_ms` | Histogram | `url`, `method`, `status_code`, `service_name` | 第三方 API 耗时 |
| 外部 API | `third_party_api_request_error_total` | Counter | `url`, `method`, `status_code`, `service_name` | 第三方 API 错误累计数 |
| DBM | `dbm_api_sync_metadata_total` | Counter | `api_name`, `service_id`, `service_name` | 元数据同步次数 |
| DBM | `dbm_api_sync_metadata_request_time_consuming_ms` | Histogram | `api_name`, `service_id`, `service_name` | 元数据同步耗时 |
| DBM | `dbm_api_sync_metadata_request_error_total` | Counter | `api_name`, `service_id`, `service_name` | 元数据同步错误累计数 |
| DBM | `dbm_api_query_metadata_request_time_consuming_ms` | Histogram | `api_name`, `service_id`, `service_name`, `status_code` | 元数据查询耗时 |
| DBM | `dbm_api_query_metadata_request_error_total` | Counter | `api_name`, `service_id`, `service_name`, `status_code` | 元数据查询错误累计数 |
| DBM | `dbm_api_query_metadata_ip_count` | Gauge | `api_name`, `service_id`, `service_name` | 单次元数据查询涉及的 IP 数 |
| SSH | `detector_ssh_time_consuming_ms` | Histogram | `service_id`, `service_name`, `status_code` | SSH 二次探测耗时 |
| SSH | `detector_ssh_error_total` | Counter | `service_id`, `service_name`, `status_code` | SSH 二次探测错误累计数 |
| 覆盖 | `dbm_metadata_save_time_consuming_ms` | Histogram | `service_id`, `service_name` | 元数据落库耗时 |
| 覆盖 | `dbm_metadata_updated_count` | Gauge | `service_id`, `service_name`, `db_type` | 统计窗口内更新的元数据行数 |
| 覆盖 | `dbha_data_status_updated_count` | Gauge | `service_id`, `service_name`, `db_type`, `harvest_type` | 统计窗口内更新的实例数 |
| 覆盖 | `dbha_data_status_updated_ip_count` | Gauge | `service_id`, `service_name`, `db_type`, `harvest_type` | 统计窗口内更新的 IP 数 |
| 覆盖 | `dbha_data_status_active_ip_count` | Gauge | `service_id`, `service_name`, `db_type` | 统计窗口内持续上报的 IP 数，不是部署总量 |

有限标签取值：

| 标签 | 取值 |
| --- | --- |
| `service_name` | `analysis` |
| `query_type` | `read_metadata`、`read_skip_instances`、`read_db_status` |
| `api_name` | `query_metadata`、`sync_metadata` |

Redis 的两个切换计数已经注册，但 `internal/provider/redis/switch` 没有写入，抓取后保持为 0。

## 3. Prometheus 抓取配置

`targets` 只写 `host:port`，不要带 rc 里的 `http://`。

```yaml
scrape_configs:
  - job_name: dbha-analysis
    metrics_path: /metrics
    scrape_interval: 15s
    static_configs:
      - targets:
          - 127.0.0.1:50082
```

## 4. Grafana 变量

| 变量 | 类型 | 配置 |
| --- | --- | --- |
| `service_id` | Query | `label_values(dbha_v2_analysis_am_business_total, service_id)`，勾选 Multi-value 与 Include All，Custom all value 留空 |
| `db_type` | Query | `label_values(dbha_v2_analysis_dbha_data_status_active_ip_count, db_type)`，勾选 Multi-value 与 Include All，Custom all value 留空 |
| `rate_window` | Custom | `1m,5m,15m`，默认 `5m`，只允许单选 |

- `service_id` 在每次进程启动时随机生成 UUID。重启后变量下拉框里会出现新值，旧值只要仍在仪表盘所选时间范围内，
  也会继续出现。
- 筛选变量在查询里统一写成 `=~"$var"`。Prometheus 数据源会对多选值做正则转义并拼成 `(a|b)`。
  不要写成 `${var:regex}`：它会把 `/` 转义成 `\/`，PromQL 解析时报 `unknown escape sequence`。
- Custom all value 留空，选 All 时只展开成实际存在的取值。写成 `.*` 会同时匹配空串，把启动时生成的空标签零值序列带进查询。
- `rate_window` 不能开启 Multi-value，否则 `[$rate_window]` 会变成非法区间。
- 时间窗变量统一命名为 `rate_window`，避免与 Grafana 内置的 `$__interval` 混淆。

## 5. 看板面板

查询中的 `$变量名`（如 `$rate_window`）是 Grafana 变量，需先按第 4 节建好变量再粘贴到面板。
在 Prometheus 页面直接执行时，把 `=~"$变量名"` 中的变量替换为 `.+`，把 `$rate_window` 换成具体时间窗，例如 `5m`。
`.+` 只匹配非空取值，替换后语法不变，仍会排除空标签零值序列。

多实例部署时，聚合都在原有 `by` 标签后追加 `instance`，避免不同实例被加总。

| 行 | 面板 | 图形 | PromQL |
| --- | --- | --- | --- |
| 服务健康 | 实例存活 | Stat | `up{job="dbha-analysis"}` |
| 服务健康 | 启动时间 | Stat | `max by (instance) (dbha_v2_analysis_dbha_startup_time_sec{service_id=~"$service_id"}) * 1000` |
| 服务健康 | 负责业务数 | Stat | `sum by (instance, service_id) (dbha_v2_analysis_am_business_total{service_id=~"$service_id"})` |
| 扫描与滑窗 | 扫描吞吐 | Time series | `sum by (instance, service_id) (rate(dbha_v2_analysis_scan_business_total{service_id=~"$service_id"}[$rate_window]))` |
| 扫描与滑窗 | 扫描 P95 耗时 | Time series | `histogram_quantile(0.95, sum by (le, instance, service_id) (rate(dbha_v2_analysis_scan_business_time_consuming_ms_bucket{service_id=~"$service_id"}[$rate_window])))` |
| 扫描与滑窗 | 出队 P95 耗时 | Time series | `histogram_quantile(0.95, sum by (le, instance, service_id) (rate(dbha_v2_analysis_pop_switch_time_consuming_ms_bucket{service_id=~"$service_id"}[$rate_window])))` |
| 扫描与滑窗 | 滑窗长度 Top 10 | Time series | `topk(10, sum by (instance, biz_id) (dbha_v2_analysis_sliding_window_size{service_id=~"$service_id"}))` |
| 切换结果 | 触发切换速率 | Time series | `sum by (instance, service_id) (rate(dbha_v2_analysis_trigger_switching_instance_total{service_id=~"$service_id"}[$rate_window]))` |
| 切换结果 | 切换成功速率 | Time series | `sum by (instance, service_id) (rate(dbha_v2_analysis_switching_instance_success_total{service_id=~"$service_id"}[$rate_window]))` |
| 切换结果 | 切换失败速率 | Time series | `sum by (instance, service_id) (rate(dbha_v2_analysis_switching_instance_error_total{service_id=~"$service_id"}[$rate_window]))` |
| 切换结果 | 切换失败率 | Stat | `sum by (instance) (rate(dbha_v2_analysis_switching_instance_error_total{service_id=~"$service_id"}[$rate_window])) / clamp_min(sum by (instance) (rate(dbha_v2_analysis_switching_instance_success_total{service_id=~"$service_id"}[$rate_window])) + sum by (instance) (rate(dbha_v2_analysis_switching_instance_error_total{service_id=~"$service_id"}[$rate_window])), 1e-9)` |
| 切换结果 | 切换 P95 耗时 | Time series | `histogram_quantile(0.95, sum by (le, instance, db_type) (rate(dbha_v2_analysis_switching_time_consuming_ms_bucket{service_id=~"$service_id"}[$rate_window])))` |
| 切换结果 | MySQL 切换失败速率 | Time series | `sum by (instance, action_scope) (rate(dbha_v2_analysis_mysql_switching_error_total{action_scope!=""}[$rate_window]))` |
| 外部依赖 | DB 查询错误速率 | Time series | `sum by (instance, query_type) (rate(dbha_v2_analysis_db_query_error_total{service_id=~"$service_id"}[$rate_window]))` |
| 外部依赖 | DBM 查询 P95 | Time series | `histogram_quantile(0.95, sum by (le, instance, api_name) (rate(dbha_v2_analysis_dbm_api_query_metadata_request_time_consuming_ms_bucket{service_id=~"$service_id"}[$rate_window])))` |
| 外部依赖 | DBM 同步错误速率 | Time series | `sum by (instance, api_name) (rate(dbha_v2_analysis_dbm_api_sync_metadata_request_error_total{service_id=~"$service_id"}[$rate_window]))` |
| 外部依赖 | SSH 探测错误速率 | Time series | `sum by (instance, status_code) (rate(dbha_v2_analysis_detector_ssh_error_total{service_id=~"$service_id"}[$rate_window]))` |
| 采集覆盖 | 活跃上报 IP | Time series | `sum by (instance, db_type) (dbha_v2_analysis_dbha_data_status_active_ip_count{service_id=~"$service_id", db_type=~"$db_type"})` |
| 采集覆盖 | 更新实例数 | Time series | `sum by (instance, db_type, harvest_type) (dbha_v2_analysis_dbha_data_status_updated_count{service_id=~"$service_id", db_type=~"$db_type"})` |

- 启动时间面板的单位选 `From Now`（日期时间），乘以 1000 是因为 Grafana 按毫秒解释时间戳。
- 进程启动时，每个带标签的指标会预先生成一条标签全为空、值为 0 的序列。带 `service_id` 筛选的面板会自动排除它；
  没有其他筛选条件的分组面板，用 `!=""` 排除这条序列。

## 6. 基数说明

`url`、`switch_id`、`biz_id` 的取值会随接口地址、切换次数和业务数增长，只用于排障明细面板，不作为总览图的分组维度。
滑窗面板用 `topk` 限制每个时间点最多 10 条；时间范围内不同时刻的前 10 不同，曲线总数可能超过 10 条。

---

返回：[文档入口](../README.md)
