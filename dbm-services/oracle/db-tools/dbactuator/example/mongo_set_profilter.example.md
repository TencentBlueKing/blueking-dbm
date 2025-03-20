### mongo_set_profiler
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="mongo_set_profiler" --data_dir=/path/to/data  --backup_dir=/path/to/backup --user="xxx"  --group="xxx" --payload='{{payload_base64}}'
```


原始payload

```json
{
  "ip":"xxx",
  "port":"xxxxxxx",
  "dbName": "xxx",
  "level": 2,
  "profileSize": 4,
  "adminUsername": "xxx",
  "adminPassword": "xxx"
}
```

"level" 有三个级别，0关闭profiler，1记录超过慢语句阈值的语句，2记录所有的语句

"profileSize" 记录语句的集合大小
