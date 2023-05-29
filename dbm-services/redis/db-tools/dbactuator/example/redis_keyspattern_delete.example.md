### redis keyspattern
redis key 正则删除:
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
        "username": "xxxx",
        "project": "bk-dbm"
    },
    "bk_biz_id":"1111",
    "path": "/redis/keyfiles/20220916.cache.moyelocaltest.redistest.db/",
    "domain": "cache.moyelocaltest.redistest.db",
    "ip":"127.0.0.1",
    "ports":[46000,46001,46002,46003,46004,46005,46006,46007,46008,46009,46010,46011,46012,46013,46014],
    "start_port":0,
    "inst_num":0,
    "key_white_regex": "test*",
    "key_black_regex": "",
    "is_keys_to_be_del": true,
    "delete_rate": 20000,
    "tendisplus_delete_rate": 3000

}
```