### bkdbmon_install
bk-dbmon安装:
```sh
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="change_password"  --payload='{{payload_base64}}'
```

原始payload:
```json
{
  "ip": "1.1.1.1",
  "role": "redis_master",
  "ins_params":[
    {
      "port":"30000",
      "old_password":"xxxxx",
      "new_password":"yyyyy",
    },
    {
      "port":"30001",
      "old_password":"xxxxx",
      "new_password":"yyyyy",
    }
  ]
}
```