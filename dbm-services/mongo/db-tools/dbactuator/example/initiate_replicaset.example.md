### init_replicaset
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="init_replicaset"  --payload='{{payload_base64}}'
```
--data_dir、--backup_dir 可以留空. --user启动进程用户名，--group启动进程用户名的属组，如果为空默认都为mysql。

原始payload

```json
{
  "ip":"10.1.1.1",
  "port":27001,
  "app":"test",
  "areaId":"test1",
  "setId":"s1",
  "configSvr":false,
  "ips":[
    "10.1.1.1:27001",
    "10.1.1.2:27002",
    "10.1.1.3:27003"
  ],
  "priority":{
    "10.1.1.1:27001":1,
    "10.1.1.2:27002":1,
    "10.1.1.3:27003":0
  },
  "hidden":{
    "10.1.1.1:27001":false,
    "10.1.1.2:27002":false,
    "10.1.1.3:27003":true
  }
}
```