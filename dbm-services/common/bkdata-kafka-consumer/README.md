# 使用

```shell
bkdata-kafka-consumer -c runtime_config.yaml
```

# 配置

```yaml
bk_data_id: 蓝鲸采集 id
bk_app_code: 蓝鲸 app 名称
bk_app_secret: 蓝鲸 app key
alt_broker: 开发环境替换 kafka broker, 正式环境无需填写
api_url: 蓝鲸 api url
client_id: "backup-stm"
group_id: "backup-stm"
dsn:
  user: root
  password: 123
  address: mysql ip:port
  database: backup_stm
  charset: utf8mb4
  connection_per_partition: 2
log:
  console: true
  debug: true
  source: true
  json: false
  log_file_dir: logs
```