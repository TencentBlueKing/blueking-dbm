### mongo_set_fcv
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="mongo_set_fcv"  --payload='{{payload_base64}}'
```


原始payload

```json
{
  "ip":"1.1.1.1",
  "port":27021,
  "oldFcv": "4.0",
  "newFcv": "4.2",
  "instanceType": "mongod",
  "adminUsername":"xxx",
  "adminPassword":"xxxxxxx",
}
```

"instanceType" 参数可选值: mongod, mongos