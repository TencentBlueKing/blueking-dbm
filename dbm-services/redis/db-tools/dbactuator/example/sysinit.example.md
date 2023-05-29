### sysinit
初始化新机器:
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="sysinit" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'
```

`--data_dir`、`--backup_dir` 可以留空.  

原始payload
```json
{
    "user":"mysql",
    "password":"xxxx"
}
```