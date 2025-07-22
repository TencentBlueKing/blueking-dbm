# 说明

dbm db同步上报事件消费程序，有三个配置文件：
1. config.yaml
  主配置，主要是 kafka 的信息
2. datasource.yaml
  入库的数据源配置，比如可以配置 mysql / doris / es
  在 data.sinkers.yaml 里面设置某个事件入库哪个数据源(数据源名称)
3. data.sinkers.yaml
  入库项配置

```shell
db-event-consumer -c config.yaml
```

## 快速新增一个消费入库
(消息上报，可参考 reverseapi/cmd/dbevent-report/README.md )

支持 2 中入库方式：
### 1. 严格 schema:
步骤(strict_schema： true)：
- 需要定义 model (pkg/model/)，定义好每个字段。默认会根据 model 定义，自动 migrate 表结构。参考`BinlogFileModel`
- 注册 model (pkg/config/)
  比如 `sinker.RegisterModelSinker(&model.BinlogFileModel{})`
- 在 data.sinkers.yaml 里面配置入库
```
- topic: "mysql_binlog_result"
  model_table: "tb_mysql_binlog_result"
  strict_schema: true
  skip_migrate_schema: false
  datasource: "prod_bk_dbm_report"
  from_beginning: false
  client_id_suffix: ""
  group_id_suffix: ""
```

解释：
- model_table: model 实现的 `TableName() string` 对应的值，会根据这个值来找对应的 model 来反序列化

建议采用 `strict_schema=true` 模式，特别是如果需要自定义入库方式。

### 2. 非严格 schema
自动根据 kafka 消息的内容，使用 `map[string]interface{}` 来反序列化，然后直接生成 insert 语句。

这种方式需要提前在目标 datasource 创建好表结构，如果表结构字段缺少，会导致入库失败。

```
- topic: "mysql_binlog_result"
  model_table: "tb_mysql_binlog_result"
  strict_schema: false
  datasource: "prod_bk_dbm_report"
```
`strict_schema=false` 时，model_table 的值用于拼成 insert table name.

非严格 schema 方式可以快速验证入库效果，不用代码定义 model 。但不方便在各个环境环境移植，不推荐。

## 自定义入库方式
可以自定义 schema migrate 方式和数据入库方式，可以参考 `MysqlBackupResultModel`
### 自定义 Save
model 实现 `CustomCreator` 接口

比如 `mysql_backup_status` 这个 model，不是简单的 insert数据， 而是上报备份进度: `Begin`,`Dump`,`Tarball`,`Report`,`Done`。 

为了防止消息补录情况下导致顺序乱掉，我们不希望前面的消息覆盖后面的消息，而后面的消息是 update status 来更新原消息，这里就要实现自定义 Creator 接口。

### 自定义 Migrate
model 实现 `CustomMigrator` 接口

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
```

### datasource.yaml
```
- name: prod_bk_dbm_report
  type: mysql
  dsn:
    user: "xx"
    password: "xxxx"
    address: "x.x.x.x:3306"
    database: "dbreport"
    charset: utf8

- name: dbreport_mysql2
  type: mysql_xorm
  dsn:
    user: "xx"
    password: "xxxx"
    address: "x.x.x.x:3306"
    database: "dbreport2"
    charset: utf8
```

### data.sinkers.yaml:
```
- topic: "mysql_dbbackup_result"
  model_table: "tb_mysql_backup_result"
  datasource: "prod_bk_dbm_report"
  from_beginning: false
  client_id_suffix: ""
  group_id_suffix: ""

- topic: "mysql_binlog_result"
  model_table: "tb_mysql_binlog_result"
  datasource: "prod_bk_dbm_report"
  from_beginning: false
  client_id_suffix: ""
  group_id_suffix: ""
```