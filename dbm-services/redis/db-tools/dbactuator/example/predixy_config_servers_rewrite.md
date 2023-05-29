### predixy config servers rewrite
predixy 配置文件 servers 重写,根据 redis-cli -h $predixy_ip -p $password -a $password info 中输出的 Servers[i].CurrentIsFail 信息判断某个server是否保留在配置文件中.
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="predixy_config_servers_rewrite" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'
```

`--data_dir`、`--backup_dir` 可以留空.  

原始payload
```json
{
    "predixy_ip":"xx.xx.xx.xx",
    "predixy_port":50000,
    "to_remove_servers":[
        "a.a.a.a:30000",
        "b.b.b.b:30000"
    ]
}
```