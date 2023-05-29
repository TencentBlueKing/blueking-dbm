### add_shard_to_cluster
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="add_shard_to_cluster"  --payload='{{payload_base64}}'
```


原始payload

```json
{
  "ip":"127.0.0.1",
  "port":27021,
  "adminUsername":"xxx",
  "adminPassword":"xxxxxxx",
  "shard":{
    "test-test1-s1":"127.0.0.2:27001,127.0.0.3:27002",
    "test-test1-s2":"127.0.0.2:27004,127.0.0.3:27005",
    "test-test1-s3":"127.0.0.3:27001,127.0.0.4:27002",
    "test-test1-s4":"127.0.0.3:27004,127.0.0.4:27005"
  }
}
```