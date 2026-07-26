### remove_shard_from_cluster
从分片集群移除分片（removeShard 并轮询至 completed）:

```json
./dbactuator --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="remove_shard_from_cluster"  --payload='{{payload_base64}}'
```


原始payload

```json
{
  "ip":"127.0.0.1",
  "port":27021,
  "adminUsername":"xxx",
  "adminPassword":"xxxxxxx",
  "shards":["demo-s3","demo-s4"],
  "maxWaitSec":259200,
  "pollSec":30
}
```
