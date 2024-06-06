### replace_package
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="replace_package"  --payload='{{payload_base64}}'
```


原始payload

```json
{
  "mediapkg": {
    "pkg": "",
    "pkg_md5": "xxx"
  },
  "ip":"1.1.1.1",
  "port":27021,
  "dbVersion":"3.4.20",
  "instanceType": "mongod"
}
```

"instanceType" 为mongod或mongos