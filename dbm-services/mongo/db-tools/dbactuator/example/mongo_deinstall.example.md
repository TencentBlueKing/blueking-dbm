### mongo_deinstall
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="mongo_deinstall"  --payload='{{payload_base64}}'
```

原始payload
```json
{
  "ip":"10.1.1.1",
  "port":27002,
  "app":"test",
  "areaId":"test1",
  "nodeInfo":[
    "10.1.1.1",
    "10.1.1.2"
  ],
  "instanceType":"mongod"
}
```

