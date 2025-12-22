# Kafka 消费指标收集和上报功能

## 功能概述

db-event-consumer 服务实现了对 Kafka topic 消费情况的统计和监控功能，包括：

- 消费次数统计
- 消费成功次数统计
- 消费失败次数统计
- 消费消息数量统计

统计结果会定时上报到蓝鲸监控平台。

## 指标说明

### 1. kafka_consume_total
- **类型**: Counter
- **说明**: Kafka 消费尝试总次数
- **标签**:
  - `topic`: Kafka topic 名称
  - `model_table`: 数据库表名
  - `writer`: 数据源写入器类型
  - `group_id`: Kafka 消费者组 ID

### 2. kafka_consume_success_total
- **类型**: Counter
- **说明**: Kafka 消费成功总次数
- **标签**: 同上

### 3. kafka_consume_failed_total
- **类型**: Counter
- **说明**: Kafka 消费失败总次数
- **标签**: 同上

### 4. kafka_consume_messages_total
- **类型**: Counter
- **说明**: Kafka 消费的消息总数量
- **标签**: 同上

### 5. kafka_fatal_errors_total
- **类型**: Counter
- **说明**: 致命错误总次数（如 Setup 失败、Schema 迁移失败等）
- **标签**:
  - `topic`: Kafka topic 名称
  - `model_table`: 数据库表名
  - `writer`: 数据源写入器类型
  - `group_id`: Kafka 消费者组 ID
  - `error_type`: 错误类型（如 `setup_error`）

## 配置说明

在 `config.yaml` 中添加 `bkm_dbm_report` 配置项：

```yaml
bkm_dbm_report:
  event:
    token: "8110c37124074527969a499f74336ac9"
    data_id: 553411
  proxy: "http://bk-report-1.woa.com:10205/v2/push/"
  metric:
    token: "4d3343a2592543c6a714781bb9583d0e"
    data_id: 553410
```

### 配置项说明

- `event`: 事件上报配置（预留）
  - `token`: 事件数据通道验证码
  - `data_id`: 事件数据通道标识
- `proxy`: 蓝鲸监控上报代理地址
- `metric`: 指标上报配置
  - `token`: 指标数据通道验证码
  - `data_id`: 指标数据通道标识

**注意**: 如果不配置 `bkm_dbm_report`，指标收集功能仍然会工作，但不会上报到蓝鲸监控平台。

## 上报格式

上报到蓝鲸监控的数据格式如下：

```json
{
  "data_id": 553410,
  "access_token": "4d3343a2592543c6a714781bb9583d0e",
  "data": [
    {
      "metrics": {
        "kafka_consume_total": 100,
        "kafka_consume_success_total": 95,
        "kafka_consume_failed_total": 5,
        "kafka_consume_messages_total": 1000,
        "kafka_fatal_errors_total": 2
      },
      "target": "mysql_backup_result",
      "dimension": {
        "model_table": "mysql_backup_result",
        "writer": "mysql",
        "group_id": "mysql_backup_result_consumer_group",
        "error_type": "setup_error"
      },
      "timestamp": 1766402835185
    }
  ]
}
```

### 字段说明

- `data_id`: 数据通道标识
- `access_token`: 数据通道验证码
- `data`: 数据数组
  - `metrics`: 指标数据（key-value 形式）
  - `target`: 目标标识（使用 topic 名称）
  - `dimension`: 自定义维度
    - `model_table`: 数据库表名
    - `writer`: 数据源写入器类型
    - `group_id`: Kafka 消费者组 ID
  - `timestamp`: 数据时间戳（毫秒）

## 上报频率

默认每 **1 分钟** 上报一次指标数据。

## 实现细节

### 1. 指标收集

在 `pkg/base/metrics.go` 中实现了 Prometheus 指标收集器：

```go
// 获取全局指标收集器
metrics := base.GetTopicMetrics()

// 记录消费尝试
metrics.RecordConsumeAttempt(topic, modelTable, writer, groupID, msgCount)

// 记录消费成功
metrics.RecordConsumeSuccess(topic, modelTable, writer, groupID)

// 记录消费失败
metrics.RecordConsumeFailed(topic, modelTable, writer, groupID)

// 记录致命错误
metrics.RecordFatalError(topic, modelTable, writer, groupID, errorType)
```

### 2. 指标统计位置

在 `pkg/consumer/consumer.go` 的 `HandleMessageTryBatch` 方法中进行统计：

- 每次调用时记录消费尝试次数和消息数量
- 根据处理结果记录成功或失败次数

在 `pkg/consumer/consumer.go` 的 `Setup` 方法中进行致命错误统计：

- 当 Schema 迁移失败时记录 fatal_errors
- 错误类型标记为 `setup_error`

### 3. 指标上报

在 `cmd/root.go` 中启动指标上报器：

```go
if config.MainConfig.BKMDBMReport != nil && config.MainConfig.BKMDBMReport.Proxy != "" {
    reporter := base.NewMetricsReporter(config.MainConfig.BKMDBMReport)
    reporter.StartReporting(1 * time.Minute)
}
```

## 使用示例

### 1. 启动服务

```bash
./db-event-consumer --config=config.yaml
```

### 2. 查看日志

服务启动后会输出以下日志：

```
INFO metrics reporter started proxy=http://bk-report-1.woa.com:10205/v2/push/ data_id=553410
```

每次上报成功后会输出：

```
INFO metrics reported successfully items=10
```

### 3. 监控指标

在蓝鲸监控平台可以查看以下指标：

- 各 topic 的消费速率
- 消费成功率
- 消费失败率
- 消息处理量

## 故障排查

### 1. 上报失败

如果看到以下错误日志：

```
ERROR failed to report metrics error="post report data failed: ..."
```

可能的原因：

- 网络连接问题
- 代理地址配置错误
- token 或 data_id 配置错误

### 2. 指标不准确

如果发现指标统计不准确，检查：

- 是否有多个实例在运行（每个实例独立统计）
- 消费者组配置是否正确
- 是否有消息重复消费

## 注意事项

1. 指标是累计值（Counter 类型），不会重置
2. 每个服务实例独立统计和上报
3. 上报失败不会影响消费功能
4. 建议在生产环境配置上报功能以便监控
