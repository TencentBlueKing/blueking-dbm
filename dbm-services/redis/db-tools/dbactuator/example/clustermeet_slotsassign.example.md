### redis replicaof
建立主从关系:
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="clustermeet_slotsassign" --payload='{{payload_base64}}'
```

前置工作:  
- 先运行 `./dbactuator_redis --atom-job-list="sysinit"`
- 先运行 `./dbactuator_redis --atom-job-list="redis_install"`,确保redis 已经安装ok;

原始payload
示例1:
```json
{
    "password":"xx",
    "use_for_expansion":false,//是否用于扩容，false：不是用于扩容
    "slots_auto_assign":true, //slots自动分配
    "replica_pairs":[
        {
            "master_ip":"127.0.0.1",
            "master_port":30000,
            "slave_ip":"127.0.0.1",
            "slave_port":31000,
            "slots":""
        },
        {
            "master_ip":"127.0.0.1",
            "master_port":30001,
            "slave_ip":"127.0.0.1",
            "slave_port":31001,
            "slots":""
        },
        {
            "master_ip":"127.0.0.1",
            "master_port":30002,
            "slave_ip":"127.0.0.1",
            "slave_port":31002,
            "slots":""
        }
    ]
}
```
示例2:
```json
{
    "password":"xxx",
    "use_for_expansion":true,//是否用于扩容，true ：是用于扩容
    "slots_auto_assign":false, //不自动分配slot,根据用户指定
    "replica_pairs":[
        {
            "master_ip":"127.0.0.1",
            "master_port":30000,
            "slave_ip":"127.0.0.1",
            "slave_port":31000,
            "slots":"0-4096"
        },
        {
            "master_ip":"127.0.0.1",
            "master_port":30001,
            "slave_ip":"127.0.0.1",
            "slave_port":30001,
            "slots":"4097-8193"
        },
        {
            "master_ip":"127.0.0.1",
            "master_port":30002,
            "slave_ip":"127.0.0.1",
            "slave_port":31002,
            "slots":"8194-12290"
        },
        {
            "master_ip":"127.0.0.1",
            "master_port":30003,
            "slave_ip":"127.0.0.1",
            "slave_port":31003,
            "slots":"12291-16383"
        }
    ]
}
```