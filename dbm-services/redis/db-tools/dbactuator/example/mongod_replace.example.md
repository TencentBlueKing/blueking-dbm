### mongod_replace
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="mongod_replace"  --payload='{{payload_base64}}'
```


原始payload

## mongod
```json
{
  "ip":"127.0.0.1",
  "port":27002,
  "sourceIP":"127.0.0.3",
  "sourcePort":27007,
  "sourceDown":true,
  "adminUsername":"xxx",
  "adminPassword":"xxxxxxxx",
  "targetIP":"127.0.0.1",
  "targetPort":27004,
  "targetPriority":"",
  "targetHidden":""
}
```
"sourceDown" 源端是否已down机
"targetPriority"可以指定替换节点的优先级
"targetHidden"可以指定替换节点是否为隐藏节点