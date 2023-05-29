### mongo_deinstall
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="mongo_deinstall"  --payload='{{payload_base64}}'
```

原始payload
```json
{
  "ip":"1.1.1.1",
  "port":27002,
  "setId":"test1",
  "nodeInfo":[
    "1.1.1.1",
    "1.1.1.2"
  ],
  "instanceType":"mongod",
  "force": true,
  "renameDir": true
}
```
"instanceType" 为mongod或mongos

"force" 为true时，会强制卸载，不检查是否有连接；为false时，会检查是否有连接

"renameDir" 为true时，会重命名目录；为false时，不会重命名目录
