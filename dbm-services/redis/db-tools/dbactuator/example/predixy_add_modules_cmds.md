### predixy add modules cmds
predixy 添加module命令(会重启predixy)
`./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="predixy_add_modules_cmds" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'`

`--data_dir`、`--backup_dir` 可以留空.  


原始payload
```json
{
    "ip":"a.a.a.a",
    "port":30000,
    "load_modules":"redisbloom,redisjson",
    "cluster_type": "PredixyRedisCluster"
}
```