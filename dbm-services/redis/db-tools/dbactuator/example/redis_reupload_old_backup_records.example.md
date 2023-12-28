### redis redis_reupload_old_backup_records
将最近N天的旧备份中的备份记录,重新用 dbm 的格式重新上报到bklog.
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_reupload_old_backup_records" --payload='{{payload_base64}}'
```

原始payload
```json
{
    "bk_biz_id":"200500194",
    "bk_cloud_id":"246",
    "server_ip":"a.a.a.a",
    "server_ports":[
        30000,
        30001,
        30002,
        30003
    ],
    "cluster_domain":"cache.aaaa.testapp.db",
    "cluster_type":"TwemproxyRedisInstance",
    "meta_role":"redis_master",
    "server_shards":{
        "a.a.a.a:30000":"0-104999",
        "a.a.a.a:30001":"105000-209999",
        "a.a.a.a:30002":"210000-314999",
        "a.a.a.a:30003":"315000-419999"
    },
    "records_file":"/data/dbbak/last_n_days_gcs_backup_record.txt",
    "force": true // true or false,如果某个备份记录解析出错,是否继续上传
}
```

