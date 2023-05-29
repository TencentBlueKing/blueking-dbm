### redis replicaof batch
批量建立主从关系:
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_replica_batch" --payload='{{payload_base64}}'
```

前置工作:  
- 先运行 `./dbactuator_redis --atom-job-list="sysinit"`
- 先运行 `./dbactuator_redis --atom-job-list="redis_install"`,确保redis 已经安装ok;

原始payload
```json
{
    "bacth_pairs":[
        {
            "master_ip":"127.0.0.1",
            "master_start_port":30000,
            "master_inst_num":3,
            "master_auth":"xxx",
            "slave_ip":"127.0.0.1",
            "slave_start_port":30000,
            "slave_inst_num":3,
            "slave_password":"xxx"
        }
    ]
}
```