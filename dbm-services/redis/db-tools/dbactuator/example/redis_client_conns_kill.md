### redis_client_conns_kill
redis通过client kill命令干掉客户端连接.
cluster nodes中得到的ip, info replicaton得到的master/slave ip会自动排除.
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_client_conns_kill" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'
```

`--data_dir`、`--backup_dir` 可以留空.  

原始payload
```json
{
    "ip":"xx.xx.xx.xx",
    "ports":[]
}
```