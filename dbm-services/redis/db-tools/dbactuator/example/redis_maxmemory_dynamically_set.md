### redis_maxmemory_dynamically_set
redis 动态设置maxmemory,
比如 系统总内存16GB, 可供给redis使用的 16GB*0.85=13.6GB
redis a.a.a.a:30000使用了 4GB, a.a.a.a:30001 使用了 2GB,
那么  a.a.a.a:30000的maxmemory=13.6 * 4/(4+2)=9.1GB
那么  a.a.a.a:30001的maxmemory=13.6 * 2/(4+2)=4.5GB
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_maxmemory_dynamically_set" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'
```

`--data_dir`、`--backup_dir` 可以留空.  

原始payload
```json
{
    "ip":"xx.xx.xx.xx",
    "ports":[]
}
```