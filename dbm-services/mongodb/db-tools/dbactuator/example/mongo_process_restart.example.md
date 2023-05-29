### mongo_restart
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="mongo_restart"  --payload='{{payload_base64}}'
```


原始payload

## mongod
```json
{
  "ip":"1.1.1.1",
  "port":27001,
  "instanceType":"mongod",
  "auth":true,
  "cacheSizeGB": 0,
  "mongoSConfDbOld":"",
  "MongoSConfDbNew":"",
  "adminUsername":"xxx",
  "adminPassword":"xxx",
  "onlyChangeParam": false
}
```
"cacheSizeGB" 为0，不改变大小

"onlyChangeParam" 为true，不重启mongod，仅修改配置文件；为false，既要修改配置文件，也要重启mongod

## mongos
```json
{
  "ip":"1.1.1.1",
  "port":27021,
  "instanceType":"mongos",
  "auth":true,
  "cacheSizeGB": 0,
  "mongoSConfDbOld":"1.1.1.2:27001",
  "MongoSConfDbNew":"1.1.1.2:27004",
  "adminUsername":"",
  "adminPassword":"",
  "onlyChangeParam": true
}
```

"onlyChangeParam" 为true，不重启mongos，仅修改配置文件；为false，既要修改配置文件，也要重启mongos