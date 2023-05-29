### delete_user
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="delete_user"  --payload='{{payload_base64}}'
```


原始payload
mongos删除业务用户
```json
{
  "ip":"127.0.0.1",
  "port":27023,
  "instanceType":"mongos",
  "adminUsername":"xxx",
  "adminPassword":"xxxxx",
  "username":"xx",
  "authDb":"admin"
}
```

mongod删除业务用户
```json
{
  "ip":"127.0.0.1",
  "port":27001,
  "instanceType":"mongod",
  "adminUsername":"xxx",
  "adminPassword":"xxxx",
  "username":"xx",
  "authDb":"admin"
}
```