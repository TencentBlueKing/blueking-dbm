# twemproxy 启停、下架
`./dbactuator_redis  
--uid={{uid}}
--root_id={{root_id}}
--node_id={{node_id}}
--version_id={{version_id}}
--atom-job-list="twemproxy_operate"
--payload='{{payload_base64}}'`

## 前置工作:
- 先运行 `./dbactuator_redis --atom-job-list="sysinit"`
- 先运行 `./dbactuator_redis --atom-job-list="twemproxy_install"`

原始payload
```json
{
    "ip":"127.0.0.1",
    "ports": 50000,
    "operate": "proxy_open/proxy_close/proxy_shutdown"
}
``