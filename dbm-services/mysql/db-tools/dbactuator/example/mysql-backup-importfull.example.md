
### payload

- 开始
```
{
    "extend": {
        "bk_biz_id": "0",
        "backup_type": "GZTAB",
        "file_from": {
            "path_full": "/data/dbbak/recover",
            "path_incr": "/data/dbbak/recover/binlog",
            "path_privileges": "/data/dbbak/recover"
        },
        "recover_full": true,
        "recover_incr": false,
        "recover_privileges": true,
        "concurrency": 10,
        "partial_recover": {
            "databases": "",
            "tables": "",
        },
        "check_myisam": false,
        "enable_imdepotent": false
    }
}
```

- 暂停
- 回滚