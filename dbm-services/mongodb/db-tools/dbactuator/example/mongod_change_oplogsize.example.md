### mongod_change_oplogsize
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="mongod_change_oplogsize"  --payload='{{payload_base64}}'
```


原始payload

```json
{
  "ip":"1.1.1.1",
  "port":27021,
  "adminUsername":"xxx",
  "adminPassword":"xxxxxxx",
  "newOplogSize": 10
}
```

