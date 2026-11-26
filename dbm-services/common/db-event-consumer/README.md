# 说明

dbm db同步上报事件消费程序，有三个配置文件：
1. config.yaml
  主配置，主要是 kafka 的信息
2. datasource.yaml
  入库的数据源配置，比如可以配置 mysql / doris / es
  数据源名称是与环境无关的关键字：`dbmReport` / `dbmReportRaw` / `dbmStats` / `dbmStatsHttp`，
  每个环境把同名 datasource 指向自己真实的库即可
3. data.*.yaml
  入库项配置，格式是入库项列表。程序会读取 config.yaml 同目录下所有 `data.*.yaml`

```shell
# --enable-defaults: 用代码内置的默认入库项生成 data.defaults.yaml(每次启动覆盖重写)
db-event-consumer -c config.yaml --enable-defaults

# 只校验配置并打印合并后最终生效的入库项，不连 kafka/db，可在 CI 里跑
db-event-consumer -c config.yaml --enable-defaults validate
```

运行期也可以通过 `http://127.0.0.1:<otel_port>/debug/config` 查看最终生效的入库项配置。

## 入库项配置方式

入库项的默认值全部内置在代码里(`pkg/config/builtin_sinkers.go`)。
加上 `--enable-defaults` 启动时，程序会把这些默认项生成到 `data.defaults.yaml`，
**每次启动都覆盖重写**，所以新版本新增的入库项，各环境升级二进制后自动生效，不需要逐个环境同步配置。

需要个性化调整某一项时，新建一个 `data.xxx.yaml`(文件名随意，只要匹配 `data.*.yaml`)，
把该项**完整**复制过去再改：

```yaml
# data.sinkers.yaml
# 这个环境的采集项名字不一样，并且要加大并发
- bk_collector_name: mysql_proxy_connlog_v3
  model_table: mysql_proxy_connlog
  strict_schema: true
  datasource: dbmStatsHttp
  ingest_threads: 8
  sink_batch_size: 20000
# 这个环境不需要这一项
- topic: redis_backup_progress
  model_table: tb_redis_backup_progress
  strict_schema: true
  datasource: dbmReport
  enable: false
```

合并规则：

- key 是 `model_table` + `group_id_suffix`。不用 topic/bk_collector_name 做 key，
  因为它们在不同环境可能不一样(比如采集项改名)，而 model_table 由代码定义，是稳定的
- `data.defaults.yaml` 作为默认项基底，其它 `data.*.yaml` 里 key 相同的项**整项覆盖**它，
  不做字段级合并，所以复制过去的项要把字段写全
- key 在 defaults 里不存在的，作为新增入库项。
  比如同一张表用不同的 `group_id_suffix` 可以再开一个消费者
- 为避免生效结果取决于文件名排序，同一个文件里出现重复 key、
  或两个非 defaults 文件里出现相同 key，都会直接报错
- 不想生成 defaults 文件(比如完全自己管理入库项配置)，就不要加 `--enable-defaults`，
  此时只有自己写的 `data.*.yaml` 生效

## 快速新增一个消费入库
(消息上报，可参考 reverseapi/cmd/dbevent-report/README.md )

支持 2 中入库方式：
### 1. 严格 schema:
步骤(strict_schema： true)：
- 需要定义 model (pkg/model/)，定义好每个字段。默认会根据 model 定义，自动 migrate 表结构。参考`BinlogFileModel`
- 在 `pkg/config/builtin_sinkers.go` 里注册默认入库项(同时完成 model 注册)
```go
RegisterDefaultSinker(&model.BinlogFileModel{}, SinkerConfig{
    Topic:      "mysql_binlog_result",
    ModelTable: "tb_mysql_binlog_result",
    Datasource: DsDbmReport,
})
```

解释：
- model_table: model 实现的 `TableName() string` 对应的值，会根据这个值来找对应的 model 来反序列化，
  同时它也是 data.*.yaml 覆盖默认项时的 key

建议采用 `strict_schema=true` 模式，特别是如果需要自定义入库方式。

### 2. 非严格 schema
自动根据 kafka 消息的内容，使用 `map[string]interface{}` 来反序列化，然后直接生成 insert 语句。
这种方式不需要在 db-event-consumer 里定义 model 的代码。

这种方式需要提前在目标 datasource 创建好表结构，或者在其他地方有 migrate 来维护表结构和索引约束。
如果表结构字段缺少，会导致入库失败。

```go
RegisterDefaultRawSinker(SinkerConfig{
    Topic:      "sqlserver_binlog_result",
    ModelTable: "tb_sqlserver_binlog_result",
    Datasource: DsDbmReportRaw,
    WriteMode:  cst.ModeUpsert,
})
```

- `strict_schema=false` 时，model_table 的值用于拼成 insert table name.
- `write_mode=upsert`, 当遇到冲突时，使用何种处理方式，`replace`,`upsert`,`insert_ignore`, `insert`
- `omit_fields`, 忽略哪些字段，不拼在 insert values 里

非严格 schema 方式可以快速验证入库效果，不用代码定义 model。如果你需要对上报的内容做重组，二次加工后再入库，则不适合这个方式。

## 自定义入库方式
可以自定义 schema migrate 方式和数据入库方式，可以参考 `MysqlBackupResultModel`
### 自定义 Save
model 实现 `CustomCreator` 接口

比如 `mysql_backup_status` 这个 model，不是简单的 insert数据， 而是上报备份进度: `Begin`,`Dump`,`Tarball`,`Report`,`Done`。 

为了防止消息补录情况下导致顺序乱掉，我们不希望前面的消息覆盖后面的消息，而后面的消息是 update status 来更新原消息，这里就要实现自定义 Creator 接口。

### 自定义 Migrate
model 实现 `CustomMigrator` 接口。默认可以直接在 model 上定义字段/索引信息，只有复杂场景下才需要自定义 Migrate。

比如为了将数据写入 Doris，表结构需要更复杂的自定义，可以不使用 gorm/xorm 的 AutoMigrate，而是自己写 CREATE TABLE 语句，可以实现自己的 MigrateSchema 方法。

## 开发 writer
当前实现的 writer:
- [x] mysql_writer  
- [x] mysql_xorm_writer (实验性质)
- [ ] elasticsearch_writer  
- [ ] doris_writer  

## 配置

### config.yaml:
```yaml
log:
  console: true
  debug: true
  source: true
  json: false
  log_file_dir: logs

kafka_info:
  cluster_config:
    brokers: xx.xx.xx
    port: 9092
  auth_info:
    username: xx
    password: xxxx
    sasl_mechanisms: SCRAM-SHA-512
    security_protocol: SASL_PLAINTEXT

# 入库项引用的 datasource 在 datasource.yaml 里不存在时: skip(默认，跳过并告警) / fail(启动失败)
on_missing_datasource: skip
```

### datasource.yaml
```
- name: dbmReport
  type: mysql
  dsn:
    user: "xx"
    password: "xxxx"
    address: "x.x.x.x:3306"
    database: "dbreport"
    charset: utf8

- name: dbmStats
  type: doris
  dsn:
    user: "xx"
    password: "xxxx"
    address: "x.x.x.x:9030"
    database: "dbstats"
    charset: utf8
```

### data.defaults.yaml
由 `--enable-defaults` 根据代码内置默认入库项生成，每次启动覆盖重写，不要手工修改。

### data.sinkers.yaml
只写需要个性化调整的入库项，同 key 的项整项覆盖 `data.defaults.yaml` 里的默认项：
```
# 本环境这个采集项名字不一样，并且消息量大需要加大并发
- bk_collector_name: mysql_proxy_connlog_v3
  model_table: mysql_proxy_connlog
  strict_schema: true
  datasource: dbmStatsHttp
  ingest_threads: 8
  sink_batch_size: 20000

# 本环境这个 topic 消息量大，加大并发
- topic: mysql_binlog_result
  model_table: tb_mysql_binlog_result
  strict_schema: true
  datasource: dbmReport
  ingest_threads: 4

# 本环境不需要这个入库项
- topic: redis_backup_progress
  model_table: tb_redis_backup_progress
  strict_schema: true
  datasource: dbmReport
  enable: false
```

不需要调整的入库项不用在这里出现。