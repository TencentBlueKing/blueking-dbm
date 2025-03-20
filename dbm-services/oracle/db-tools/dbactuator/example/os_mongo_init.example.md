### os_mongo_init
初始化新机器:

```json
./oracle-dbactuator  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="os_mongo_init"  --user="xxx"  --group="xxx" --payload='{{payload_base64}}'
```
--user启动进程用户名，--group启动进程用户名的属组，如果为空默认都为mysql。

原始payload

```json
{
"user":"xxx",
"password":"xxxxxxx"
}
```