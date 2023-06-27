### redis_backup
备份:
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_backup" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'
```

`--data_dir`、`--backup_dir` 可以留空.  

原始payload
```json
{
    "bk_biz_id":"1111",
    "domain": "cache.hello.testapp.db",
    "ip":"xx.xx.xx.xx",
    "ports":[],
    "start_port":30000,
    "inst_num":10,
    "backup_type":"normal_backup",
    "without_to_backup_sys":true, //是否上传到备份系统,默认false
    "ssd_log_count":{ // tendisssd 重建slave做备份需设置相关参数,普通备份不传值 或 传0即可
        "log-count":8000000,
        "log-keep-count":800000,
        "slave-log-keep-count":5000000
    }
}
```