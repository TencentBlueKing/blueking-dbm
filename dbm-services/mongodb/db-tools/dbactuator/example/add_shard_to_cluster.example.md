### add_shard_to_cluster
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="add_shard_to_cluster"  --payload='{{payload_base64}}'
```


原始payload

```json
{
  "ip":"1.1.1.1",
  "port":27021,
  "adminUsername":"xxx",
  "adminPassword":"xxxxxxx",
  "shard":{
    "test-test1-s1":"1.1.1.2:27001,1.1.1.3:27002",
    "test-test1-s2":"1.1.1.2:27004,1.1.1.3:27005",
    "test-test1-s3":"1.1.1.3:27001,1.1.1.4:27002",
    "test-test1-s4":"1.1.1.3:27004,1.1.1.4:27005"
  }
}
```