# dbactuator mysql deploy-dbbackup 

### 原始payload
{
    "general":{
       "runtime_account":{
        "admin_user":"xx",
        "admin_pwd": "xx",
        "monitor_user":"xx",
        "monitor_pwd":"xx",
        "monitor_access_all_user":"xx",
        "monitor_access_all_pwd":"xx",
        "repl_user":"xx",
        "repl_pwd":"xx",
        "backup_user":"xx",
        "backup_pwd":"xx",
        "yw_user":"xx",
        "yw_pwd": "xx"
        "proxy_admin_user": "xx",
        "proxy_admin_pwd": "xx"
     }
    },
"extend":{
    "pkg": "backup_1.0.15.tar.gz",
    "pkg_md5": "20bc5a0172c72991d499bdb079fea445",
    "app": "test_app",
    "role": "MASTER",
    "exec_user": "",
    "configs": [
        {
            "bk_biz_id": "0",
            "level_name": "plat",
            "level_value": "0",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "MysqlBackup",
                "conf_file": "dbbackup.conf",
                "conf_type_lc": "",
                "conf_file_lc": "",
                "namespace_info": "",
                "description": "",
                "updated_by": "",
                "created_at": "",
                "updated_at": ""
            },
            "content": {
                "BackTimeOut": "09:00:00",
                "BackType": "GZTAB",
                "BackupDir": "/data/dbbak",
                "CrontabTime": "3 5 * * *",
                "DataOrGrant": "ALL",
                "FlushRetryCount": "3",
                "FlushWaitTimeout": "30",
                "LargetableSize": "10G",
                "MysqlBinPath": "/usr/local/mysql/bin",
                "MysqlCharset": "utf8mb4",
                "MysqlHost": "DEFAULT",
                "MysqlIgnoreDbList": "performance_schema information_schema mysql test infodba_schema",
                "MysqlPass": "DEFAULT",
                "MysqlPort": "3306",
                "MysqlRole": "MASTER",
                "MysqlUser": "DEFAULT",
                "OldFileLeftDay": "2",
                "ProductName": "DEFAULT",
                "SplitCount": "10"
            }
        },
        {
            "bk_biz_id": "0",
            "level_name": "plat",
            "level_value": "0",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "MysqlBackup",
                "conf_file": "local_backup_config_not_upload",
                "conf_type_lc": "",
                "conf_file_lc": "",
                "namespace_info": "",
                "description": "",
                "updated_by": "",
                "created_at": "",
                "updated_at": ""
            },
            "content": {
                "MaxConcurrency": "1",
                "MaxResourceUsePercent": "90",
                "SlowQueryWhiteUsers": "repl,system user,event_scheduler,dnf_oss",
                "TarAndSplitSpeedLimit": "200"
            }
        }
    ],
    "host": "127.0.0.1",
    "ports": [
        20000
    ]
    }
}
```