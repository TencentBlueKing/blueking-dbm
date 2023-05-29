## 公共配置文件

**获取**

**保存并发布**

## my.cnf 配置项

**获取**


**保存并发布**

## 部署配置
**获取**
```
{
    "code": 0,
    "message": "",
    "data": [
        {
            "bk_biz_id": "testapp",
            "level_name": "cluster",
            "level_value": "act3",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "deploy",
                "conf_file": "tb_app_info",
                "conf_type_lc": "部署配置",
                "conf_file_lc": "",
                "namespace_info": "",
                "description": "",
                "updated_by": "",
                "created_at": "",
                "updated_at": ""
            },
            "content": {
                "charset": "utf8mb4",
                "major_version": "mysql-5.6",
                "mycnf_template": "my.cnf#5.6",
                "storage_engine": "innodb"
            }
        }
    ]
}
```

response:
```
{
    "code": 0,
    "message": "",
    "data": [
        {
            "bk_biz_id": "testapp",
            "level_name": "module",
            "level_value": "act",
            "conf_type": "deploy",
            "conf_file": "tb_app_info",
            "content": {
                "charset": "utf8mb4",
                "major_version": "mysql-5.6"
            }
        }
    ]
}
```

## 初始权限配置
**获取**
```
curl --location --request POST 'http://localhost:8080/bkconfig/v1/confitem/query' \
--header 'Content-Type: application/json' \
--data-raw '{
    "bk_biz_id":"testapp",
    "level_name":"pub",
    "level_value":"0",
    "conf_file":"mysql#user,proxy#user",
    "conf_type":"init_user",
    "namespace":"tendbha",
    "format":"map"
}'
```

response:
```
{
    "code": 0,
    "message": "",
    "data": [
        {
            "bk_biz_id": "0",
            "level_name": "plat",
            "level_value": "0",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "init_user",
                "conf_file": "mysql#user",
                "conf_type_lc": "",
                "conf_file_lc": "初始化用户",
                "namespace_info": "",
                "description": "我是描述",
                "updated_by": "",
                "created_at": "",
                "updated_at": ""
            },
            "content": {
                "admin_pwd": "xx",
                "admin_user": "xx"
            }
        },
        {
            "bk_biz_id": "0",
            "level_name": "plat",
            "level_value": "0",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "init_user",
                "conf_file": "proxy#user",
            },
            "content": {
                "proxy_admin_pwd": "xx",
                "proxy_admin_user": "xx"
            }
        },
        {
            "bk_biz_id": "0",
            "level_name": "plat",
            "level_value": "0",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "init_user",
                "conf_file": "mysql_os#user",
            },
            "content": {
                "os_mysql_pwd": "xx",
                "os_mysql_user": "xx"
            }
        }
    ]
}
```

## 监控配置
**获取**
```
curl --location --request POST 'http://localhost:8080/bkconfig/v1/confitem/query' \
--header 'Content-Type: application/json' \
--data-raw '{
    "bk_biz_id":"0",
    "level_name":"plat",
    "level_value":"0",
    "conf_file":"db_monitor,global_status",
    "conf_type":"MysqlMasterMonitor",
    "namespace":"tendbha",
    "format":"map"
}'
```

response:
```
{
    "code": 0,
    "message": "",
    "data": [
        {
            "bk_biz_id": "0",
            "level_name": "plat",
            "level_value": "0",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "MysqlMasterMonitor",
                "conf_file": "db_monitor",
            },
            "content": {
                "conn_log": "{\"check\": \"YES\",\"expire_days\": \"1\",\"max_size\": \"2G\"}",
                ...
                "myisam_check": "{\"check\": \"YES\"}",
                "unnormal_sql_check": "{\"accounts\": \"event_scheduler\",\"check\": \"YES\",\"timelimit\": \"18000\"}",
                "warn_level.DB_DEADLOCK_check": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"0\",\"repeat\": \"2\",\"unimportance_time\": \"0 0\"}",
                "warn_level.DB_SQL_check": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"2\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                ...
                "warn_swith": "{\"valve\": \"OPEN\"}"
            }
        },
        {
            "bk_biz_id": "0",
            "level_name": "plat",
            "level_value": "0",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "MysqlMasterMonitor",
                "conf_file": "global_status"
            },
            "content": {
                "Aborted_clients": "{\"is_additive\": \"1\",\"is_ignore\": \"1\",\"is_number\": \"1\",\"valve\": \"100000000\"}",
                ...
                "spin_waits": "{\"is_additive\": \"1\",\"is_ignore\": \"1\",\"is_number\": \"1\",\"tnm_id\": \"1029\",\"valve\": \"100000000\"}"
            }
        }
    ]
}

```