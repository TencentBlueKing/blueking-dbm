### init_replicaset
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="init_replicaset"  --payload='{{payload_base64}}'
```

原始payload

```json
{
  "ip":"1.1.1.1",
  "port":27001,
  "setId":"s1",
  "configSvr":false,
  "ips":[
    "1.1.1.1:27001",
    "1.1.1.2:27002",
    "1.1.1.3:27003"
  ],
  "priority":{
    "1.1.1.1:27001":1,
    "1.1.1.2:27002":1,
    "1.1.1.3:27003":0
  },
  "hidden":{
    "1.1.1.1:27001":false,
    "1.1.1.2:27002":false,
    "1.1.1.3:27003":true
  }
}
```