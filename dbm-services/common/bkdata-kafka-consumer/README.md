# 使用

```shell
bkdata-kafka-consumer -c config.yaml
```

# 配置

config.yaml:
```yaml
bk_app_code: 蓝鲸 app 名称
bk_app_secret: 蓝鲸 app key
alt_broker: 开发环境替换 kafka broker, 正式环境无需填写
api_url: 蓝鲸 api url

log:
  console: true
  debug: true
  source: true
  json: false
  log_file_dir: logs
```

data.xxx.yaml:
```
bk_data_id: 蓝鲸采集 id
client_id: "backup-stm"
group_id: "backup-stm"
from_beginning: false
sink_batch_size: 1
fetch_min_bytes: 1024
dsn:
  user: root
  password: 123
  address: mysql ip:port
  database: backup_stm
  charset: utf8mb4
  connection_per_partition: 2
```