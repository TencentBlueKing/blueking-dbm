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
  "singleNodeInstallRestart":false,  
  "auth":true,
  "cacheSizeGB": null,
  "mongoSConfDbOld":"",
  "MongoSConfDbNew":"",
  "adminUsername":"",
  "adminPassword":""
}
```
"singleNodeInstallRestart"字段表示安装替换节点时mongod单节点重启  true：替换节点单节点重启 false：复制集节点重启
"adminUsername"和"adminPassword"字段为空时表示安装时最后一步重启进程，不为空时表示提供服务期间重启
## mongos
```json
{
  "ip":"1.1.1.1",
  "port":27021,
  "instanceType":"mongos",
  "singleNodeInstallRestart":false,
  "auth":true,
  "cacheSizeGB": null,
  "mongoSConfDbOld":"1.1.1.2:27001",
  "MongoSConfDbNew":"1.1.1.2:27004",
  "adminUsername":"",
  "adminPassword":""
}
```