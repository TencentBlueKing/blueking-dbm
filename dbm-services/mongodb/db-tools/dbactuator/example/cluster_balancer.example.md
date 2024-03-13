### mongod_replace
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="cluster_balancer"  --payload='{{payload_base64}}'
```


原始payload

```json
{
  "ip":"1.1.1.1",
  "port":27021,
  "open": false,
  "adminUsername":"xxx",
  "adminPassword":"xxxxxxxxx"
}
```
"open"字段 true：表示打开balancer  false：表示关闭balancer
