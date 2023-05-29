### redis keyspattern
redis key 结果文件删除:
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="tendis_keyspattern"  --payload='{{payload_base64}}'
```

`--data_dir`、`--backup_dir` 留空.  
前置工作:  初始化机器和安装完成redis
- 运行 `./dbactuator_redis --atom-job-list="sysinit"`
- 运行 `./dbactuator_redis --atom-job-list="redis_install"`

原始payload
```json

{
    "pkg":"keytools.tag.gz",
    "pkg_md5":"e0598229d65e1232b33f60a56e16cd0a",
    "fileserver": {
        "url": "介质库https地址",
        "bucket": "bk-dbm-redistest",
        "password": "xxxx",
        "username": "xxx",
        "project": "bk-dbm"
    },
    "bk_biz_id":"1111",
    "path": "/redis/keyfiles/20220919.cache2006.moyecachetest.redistest.db",
    "domain": "cache2006.moyecachetest.redistest.db",
    "proxy_port":52006,
    "proxy_password":"xxxx",
    "tendis_type":"TwemproxyRedisInstance",
    "delete_rate": 20000,
    "tendisplus_delete_rate": 3000

}
```