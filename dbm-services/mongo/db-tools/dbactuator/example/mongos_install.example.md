### mongos_install
初始化新机器:

```json
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="mongos_install" --data_dir=/path/to/data  --backup_dir=/path/to/backup --user="xxx"  --group="xxx" --payload='{{payload_base64}}'
```
--data_dir、--backup_dir 可以留空. --user启动进程用户名，--group启动进程用户名的属组，如果为空默认都为mysql。

原始payload

```json
{
  "mediapkg":{
    "pkg":"mongodb-linux-x86_64-3.4.20.tar.gz",
    "pkg_md5":"e68d998d75df81b219e99795dec43ffb"
  },
  "ip":"10.1.1.1",
  "port":27021,
  "dbVersion":"3.4.20",
  "instanceType":"mongos",
  "app":"test",
  "areaId":"test1",
  "auth": true,
  "configDB":["10.1.1.2:27001","10.1.1.3:27002","10.1.1.4:27003"],
  "dbConfig":{
    "slowOpThresholdMs":200,
    "destination":"file"
  }
}
```