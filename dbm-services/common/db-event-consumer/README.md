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
支持 2 中入库方式：
### 1. 严格 schema:
strict_schema： true

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

建议采用 strict_schema 模式，特别是如果需要自定义入库方式。

### 2. 非严格 schema
自动根据 kafka 消息的内容，使用 `map[string]interface{}` 来反序列化，然后直接生成 insert 语句。

这种方式需要提前在目标 datasource 创建好表结构，如果表结构字段缺少，会导致入库失败。

```
- topic: "mysql_binlog_result"
  model_table: "tb_mysql_binlog_result"
  strict_schema: false
  datasource: "prod_bk_dbm_report"
```

## 自定义入库方式
可以自定义 schema migrate 方式和数据入库方式，可以参考 `MysqlBackupResultModel`
### 自定义 Save
model 实现 `CustomCreator` 接口

### 自定义 Migrate
model 实现 `CustomMigrator` 接口

## 开发 writer


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
    domain_name: xx.xx.xx
    port: 9092
  auth_info:
    username: xx
    password: xxxx
    sasl_mechanisms: SCRAM-SHA-512
    security_protocol: SASL_PLAINTEXT
```

### datasource.yaml
```
- name: dbreport_mysql
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
  datasource: "dbreport_mysql"
  from_beginning: false
  client_id_suffix: ""
  group_id_suffix: ""

- topic: "mysql_binlog_result"
  model_table: "tb_mysql_binlog_result"
  datasource: "dbreport_mysql"
  from_beginning: false
  client_id_suffix: ""
  group_id_suffix: ""
```