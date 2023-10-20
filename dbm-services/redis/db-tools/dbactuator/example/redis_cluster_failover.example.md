### redis cluster failover
redis cluster failover
`./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_cluster_failover" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'`

`--data_dir`、`--backup_dir` 可以留空.  


原始payload
```json
{
    "redis_password":"xxxx",
    "redis_master_slave_pairs":[
        {
            "master": {"ip":"a.a.a.a","port":"30000"},
            "slave": {"ip":"b.b.b.b","port":"30000"}
        },
        {
            "master": {"ip":"a.a.a.a","port":"30001"},
            "slave": {"ip":"b.b.b.b","port":"30001"}
        }
    ],
    "force":false
}
```