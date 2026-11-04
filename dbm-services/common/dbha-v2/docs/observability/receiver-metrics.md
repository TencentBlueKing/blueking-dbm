# Receiver 指标与 Grafana 配置

本文汇总 receiver 暴露的 Prometheus 指标，并给出 Grafana 抓取与看板配置。同系列文档：
[analysis 指标](analysis-metrics.md)、[admin 指标](admin-metrics.md)。

## 1. 暴露方式

- 监听地址取自 `receiver.yaml` 的 `apm.listenAddress`，指标路径为 `/metrics`，同端口提供 `/health`。
  实现见 [pkg/haapm/server.go](../../pkg/haapm/server.go)。
- 示例地址取自 [etc/dbha-v2.server.rc.example](../../etc/dbha-v2.server.rc.example) 的
  `RECEIVER_APM_LISTEN_ADDRESS`，为 `127.0.0.1:50081`。该变量为空时，渲染脚本会改用本机自动检测的 IPv4。
- 下文指标名统一省略前缀 `dbha_v2_receiver_`。

> 代码里的 Subsystem 为 `dbha-v2-receiver`（[internal/receiver/service.go](../../internal/receiver/service.go)），
> haapm 原样传给 client_golang（v1.23.2），可以正常注册。`/metrics` 默认把名称里的 `-` 转义为 `_`，输出
> `dbha_v2_receiver_*`，本文查询按此书写。抓取方在 `Accept` 中声明 `escaping=allow-utf-8` 时会输出原始名称，
> 形如 `{"dbha-v2-receiver_kafka_read_messages_total",...}`，此时本文查询匹配不到。

`/metrics` 还会带上 Prometheus 客户端默认的 `go_*`、`process_*`，不属于 receiver 业务指标，下表不列。
Histogram 在抓取结果里展开为 `_bucket`、`_sum`、`_count`，下表写基础名。

## 2. 指标清单

业务指标共 20 个，定义见 [internal/receiver/apm/metric.go](../../internal/receiver/apm/metric.go)。

| 分组 | 指标名 | 类型 | 标签 | 含义 |
| --- | --- | --- | --- | --- |
| 服务 | `dbha_startup_time_sec` | Gauge | `service_id`, `service_name` | 进程启动的 Unix 时间，单位秒；help 写作运行时长，与实际值不符 |
| Kafka | `kafka_read_messages_total` | Counter | `kafka` | 从 Kafka 读到的消息累计数 |
| Kafka | `kafka_read_bytes_total` | Counter | `kafka` | 从 Kafka 读到的字节累计数 |
| Kafka | `kafka_write_errors_total` | Counter | `kafka` | Kafka 消息写入存储失败的消息数，含 panic 与降级超时；help 写作写入 Kafka 的错误，与实际不符 |
| Kafka | `kafka_consume_delay_ms` | Histogram | `kafka` | 一批消息处理结束时刻减去 Kafka 消息时间戳，单位 ms；写入失败的消息也计入，时间戳为零的跳过 |
| MySQL | `mysql_write_messages_total` | Counter | `mysql` | 写入 MySQL 的消息累计数 |
| MySQL | `mysql_write_bytes_total` | Counter | `mysql` | 写入 MySQL 的字节累计数 |
| MySQL | `mysql_write_duration_ms` | Histogram | `mysql` | 单条写入耗时，单位 ms |
| MySQL | `mysql_batch_write_duration_ms` | Histogram | `mysql` | 按端点的批量写入耗时，单位 ms |
| MySQL | `mysql_write_batch_size` | Histogram | `mysql` | 去重后每批行数 |
| MySQL | `mysql_write_errors_total` | Counter | `mysql` | 写入错误累计数 |
| MySQL | `mysql_read_errors_total` | Counter | `mysql` | 读取错误累计数 |
| MySQL | `mysql_dedup_dropped_total` | Counter | `mysql` | 批内主键去重丢弃的累计数 |
| MySQL | `mysql_batch_fallback_total` | Counter | `mysql` | 因数据错误退回逐行写的次数 |
| MySQL | `mysql_retry_total` | Counter | `mysql` | 分片写入重试次数 |
| Probe | `probe_receive_messages_total` | Counter | `probe` | 从 Probe 收到的消息累计数 |
| Probe | `probe_receive_bytes_total` | Counter | `probe` | 从 Probe 收到的字节累计数 |
| Probe | `probe_queue_full_total` | Counter | `probe` | Probe 入队时队列已满的次数 |
| Sink | `sink_write_delay_ms` | Histogram | `sink`, `db_type` | 从 `report_timestamp` 到成功落库的延迟，单位 ms |
| Sink | `sink_drop_messages_total` | Counter | `sink`, `db_type`, `reason` | 未写入存储或被主动丢弃的消息数 |

标签取值：

| 标签 | 取值 |
| --- | --- |
| `kafka` | 消息所属的 Kafka topic |
| `mysql` | Kafka 消息为所属 topic；Probe 直连上报固定为 `probe` |
| `sink` | Kafka 消息为所属 topic；Probe 直连上报固定为 `probe` |
| `probe` | 固定为 `probe` |
| `db_type` | 消息解析出的 DB 类型；尚未解析出类型就被丢弃时为空串 |
| `reason` | `stale`、`no_sink`、`empty`、`queue_full`、`sink_closed`、`invalid_json`、`unknown_type`、`dedup`、`data_error`、`retry_timeout`、`fatal`、`write_error`、`degrade_timeout`、`panic` |

- `reason` 常量定义见 [internal/receiver/sink/stats.go](../../internal/receiver/sink/stats.go)。内部值 `ctx_done` 不会成为标签。
- `mysql_write_batch_size` 的桶复用了耗时桶 `1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000`，按行数解读。
- `sink_write_delay_ms` 的桶为 `1000` 到 `300000` ms，覆盖 60 秒分析窗口和最长 5 分钟的延迟写入。

## 3. Prometheus 抓取配置

`targets` 只写 `host:port`，不要带 rc 里的 `http://`。

```yaml
scrape_configs:
  - job_name: dbha-receiver
    metrics_path: /metrics
    scrape_interval: 15s
    static_configs:
      - targets:
          - 127.0.0.1:50081
```

## 4. Grafana 变量

| 变量 | 类型 | 配置 |
| --- | --- | --- |
| `db_type` | Query | `label_values({__name__=~"dbha_v2_receiver_sink_.+"}, db_type)`，勾选 Multi-value 与 Include All，Custom all value 留空 |
| `rate_window` | Custom | `1m,5m,15m`，默认 `5m`，只允许单选 |

- `db_type` 同时取自 `sink_write_delay_ms` 与 `sink_drop_messages_total`。前者只在写入成功时记录，只取它会漏掉
  只出现在丢弃里的 `db_type`（如整段时间都写入失败的类型、`unknown_type` 带的未知类型），选 All 时丢弃面板会把它们过滤掉。

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
| 服务 | 实例存活 | Stat | `up{job="dbha-receiver"}` |
| 服务 | 启动时间 | Stat | `max by (instance) (dbha_v2_receiver_dbha_startup_time_sec) * 1000` |
| Probe | 接收速率 | Time series | `sum by (instance) (rate(dbha_v2_receiver_probe_receive_messages_total[$rate_window]))` |
| Probe | 接收字节速率 | Time series | `sum by (instance) (rate(dbha_v2_receiver_probe_receive_bytes_total[$rate_window]))` |
| Probe | 队列满速率 | Time series | `sum by (instance) (rate(dbha_v2_receiver_probe_queue_full_total[$rate_window]))` |
| Kafka | 读取速率 | Time series | `sum by (instance) (rate(dbha_v2_receiver_kafka_read_messages_total[$rate_window]))` |
| Kafka | 写入失败速率 | Time series | `sum by (instance) (rate(dbha_v2_receiver_kafka_write_errors_total[$rate_window]))` |
| Kafka | 消费延迟 P95 | Time series | `histogram_quantile(0.95, sum by (le, instance) (rate(dbha_v2_receiver_kafka_consume_delay_ms_bucket[$rate_window])))` |
| MySQL | 写入速率 | Time series | `sum by (instance) (rate(dbha_v2_receiver_mysql_write_messages_total[$rate_window]))` |
| MySQL | 写入错误速率 | Time series | `sum by (instance) (rate(dbha_v2_receiver_mysql_write_errors_total[$rate_window]))` |
| MySQL | 重试与逐行回退速率 | Time series | 两条查询，见下方「重试与逐行回退速率」代码块 |
| MySQL | 批量写入 P95 | Time series | `histogram_quantile(0.95, sum by (le, instance) (rate(dbha_v2_receiver_mysql_batch_write_duration_ms_bucket[$rate_window])))` |
| MySQL | 每批行数 P50 | Time series | `histogram_quantile(0.5, sum by (le, instance) (rate(dbha_v2_receiver_mysql_write_batch_size_bucket[$rate_window])))` |
| Sink | 落库延迟 P95 | Time series | `histogram_quantile(0.95, sum by (le, instance, db_type) (rate(dbha_v2_receiver_sink_write_delay_ms_bucket{db_type=~"$db_type"}[$rate_window])))` |
| Sink | 丢弃速率 | Time series | 见下方「丢弃速率」代码块 |

重试与逐行回退速率，同一面板放两个 Query。Query A 为分片写入重试：

```promql
sum by (instance) (rate(dbha_v2_receiver_mysql_retry_total[$rate_window]))
```

Query B 为逐行回退：

```promql
sum by (instance) (rate(dbha_v2_receiver_mysql_batch_fallback_total[$rate_window]))
```

丢弃速率：

```promql
sum by (instance, db_type, reason) (rate(dbha_v2_receiver_sink_drop_messages_total{db_type=~"$db_type|", reason!=""}[$rate_window]))
```

- 丢弃速率面板的 `db_type` 匹配末尾带 `|`，用于同时匹配空串。`stale`、`no_sink`、`empty`、`queue_full`、`sink_closed`、
  `invalid_json`、`degrade_timeout`、`panic` 上报时 `db_type` 为空；`write_error` 在 Kafka 消费路径上为空，在单条写入路径上带
  `db_type`。只按 `$db_type` 过滤会漏掉这些丢弃。`unknown_type`、`dedup`、`data_error`、`retry_timeout`、`fatal`
  带解析出的 `db_type`。
- 进程启动时，每个带标签的指标会预先生成一条标签全为空、值为 0 的序列。没有其他筛选条件的分组面板，用 `!=""` 排除这条序列。
- 启动时间面板的单位选 `From Now`（日期时间），乘以 1000 是因为 Grafana 按毫秒解释时间戳。
- 落库延迟 P95 接近 60000 ms 时，数据已接近 analysis 的指标读取窗口（`readDbMetricOffsetDuration`，默认 `-60s`）。

## 6. 基数说明

`kafka`、`mysql`、`sink` 的取值是 topic 或 `probe`，只用于排障明细面板，总览按 `instance`、`db_type` 或 `reason` 聚合。

---

返回：[文档入口](../README.md)
