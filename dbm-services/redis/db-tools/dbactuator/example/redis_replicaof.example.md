### redis replicaof
建立主从关系:
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_replicaof" --payload='{{payload_base64}}'
```

前置工作:  
- 先运行 `./dbactuator_redis --atom-job-list="sysinit"`
- 先运行 `./dbactuator_redis --atom-job-list="redis_install"`,确保redis 已经安装ok;

原始payload
```json
{
    "replica_pairs":[
        {
            "master_ip":"127.0.0.1",
            "master_port":30000,
            "master_auth":"xxx",
            "slave_ip":"127.0.0.1",
            "slave_port":31000,
            "slave_password":"xxxx"
        },
        {
            "master_ip":"127.0.0.1",
            "master_port":30001,
            "master_auth":"xxx",
            "slave_ip":"127.0.0.1",
            "slave_port":31001,
            "slave_password":"xxx"
        }
    ]
}
```

