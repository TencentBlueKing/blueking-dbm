### bkdbmon_install
bk-dbmon安装:
```sh
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="bkdbmon_install"  --payload='{{payload_base64}}'
```

原始payload:
```json
{
    "bkdbmonpkg":{
        "pkg":"bk-dbmon-v0.2.tar.gz",
        "pkg_md5":"99081e28443d0615b151ae82e74b69e4"
    },
    "dbtoolspkg":{
        "pkg":"dbtools.tar.gz",
        "pkg_md5":"334cf6e3b84d371325052d961584d5aa"
    },
    "gsepath":"/usr/local/gse_bkte",
    "redis_fullbackup":{
        "to_backup_system":"yes",
        "old_file_left_day":2,
        "cron":"0 5,13,21 * * *"
    },
    "redis_binlogbackup":{
        "to_backup_system":"yes",
        "old_file_left_day":2,
        "cron":"@every 10m"
    },
    "redis_heartbeat":{
        "cron":"@every 10s"
    },
    "redis_monitor":{
        "bkmonitor_event_data_id": 542898,
        "bkmonitor_event_token": "xxxxxx",
        "bkmonitor_metric_data_id": 11111,
        "bkmonitor_metirc_token": "xxxx",
        "cron":"@every 1m"
    },
    "redis_keylife":{
        "stat_dir":"/data/dbbak/keylifecycle",
        "cron":"",
        "hotkey_conf":{
            "top_count":10,
            "duration_seconds":30,
        },
        "bigkey_conf":{
            "top_count":10,
            "duration_seconds":60*60*5,
            "on_master":false,
            "use_rdb":true,
            "disk_max_usage":65,
            "keymod_spec":["axxxy","bxxr"],
            "keymod_engine":"default"
        }
    },
    "servers":[
        {
            "bk_biz_id":"200500194",
            "bk_cloud_id":"246",
            "app":"testapp",
            "app_name":"测试app",
            "cluster_domain":"cache.aaaa.testapp.db",
            "cluster_name":"aaaa",
            "cluster_type":"TwemproxyRedisInstance",
            "meta_role":"redis_master",
            "server_ip":"127.0.0.1",
            "server_ports":[
                30000,
                30001,
                30002,
                30003
            ],
            "server_shards":{
                "a.a.a.a:12000":"0-104999",
                "a.a.a.a:12001":"105000-209999",
                "a.a.a.a:12002":"210000-314999",
                "a.a.a.a:12003":"315000-419999"
            },
            "cache_backup_mode":"rdb"
        },
        {
            "bk_biz_id":"200500194",
            "bk_cloud_id":"246",
            "app":"testapp",
            "app_name":"测试app",
            "cluster_domain":"tendisx.aaaa.testapp.db",
            "cluster_name":"aaaa",
            "cluster_type":"PredixyTendisplusCluster",
            "meta_role":"redis_slave",
            "server_ip":"127.0.0.1",
            "server_ports":[
                31000,
                31001,
                31002,
                31003
            ],
            "server_shards":{},
            "cache_backup_mode":""
        }
    ]
}
```