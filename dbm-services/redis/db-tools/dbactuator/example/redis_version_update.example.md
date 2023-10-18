### redis version update
redis版本更新  
`./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_version_update" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'`

`--data_dir`、`--backup_dir` 可以留空.  

前置工作:  
- 将`redis-6.2.7.tar.gz`下载到`/data/install`目录下;  


原始payload
```json
{
    "pkg":"redis-6.2.7.tar.gz",
    "pkg_md5":"1fc9e5c3a044ce523844a6f2717e5ac3",
    "ip":"127.0.0.1",
    "ports":[30000,30001,30002], //端口不连续
    "password":"xxx",
    "role":"redis_master" // or redis_slave
}
```