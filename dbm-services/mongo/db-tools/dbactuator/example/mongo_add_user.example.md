### add_user
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="add_user"  --payload='{{payload_base64}}'
```


原始payload

创建管理员用户
```json
{
  "ip":"10.1.1.1",
  "port":27001,
  "instanceType":"mongod",
  "username":"xxx",
  "password":"xxxxxxx",
  "adminUsername":"",
  "adminPassword":"",
  "authDb":"admin",
  "dbs":[

  ],
  "privileges":[
    "root"
  ]
}
```

创建业务用户
```json
{
  "ip":"10.1.1.1",
  "port":27001,
  "instanceType":"mongod",
  "username":"xxx",
  "password":"xxxxxxx",
  "adminUsername":"xxx",
  "adminPassword":"xxxxxxxx",
  "authDb":"admin",
  "dbs":[

  ],
  "privileges":[
    "xxx"
  ]
}
```


"instanceType"字段   "mongod"：表示在复制集或者复制集单点进行创建用户  "mongos"：表示cluster进行创建用户