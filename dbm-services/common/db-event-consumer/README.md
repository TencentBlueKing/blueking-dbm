# 使用

```shell
db-event-consumer -c config.yaml
```

# 配置

config.yaml:
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

datasource.yaml
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

data.xxx.yaml:
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