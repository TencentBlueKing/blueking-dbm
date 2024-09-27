### redis_replicas_force_resync
redis slave 强制重同步.


```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_replicas_force_resync" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'
```

`--data_dir`、`--backup_dir` 可以留空.  

原始payload
```json
{
    "slave_ip":"xx.xx.xx.xx",
    "slave_ports":[30000,30001]
}
```