# dbactuator proxy deploy-monitor 
安装proxy  
`dbactuator proxy deploy-monitor  -u xx -n xx -p <base64(payload)> `   
前置工作
-  将 proxy_monitor_20210917.tar.gz 下载到 /data/install

### 原始 payload 
```
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
    "pkg": "proxy_monitor_20210917.tar.gz",
    "pkg_md5": "b315d3f16179d050c7dda66210f7b4e2",
    "app": "test_app",
    "dbas": "xx",
    "exec_user": "xx",
    "configs": [
        {
            "bk_biz_id": "0",
            "level_name": "plat",
            "level_value": "0",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "MysqlProxyMonitor",
                "conf_file": "proxy_monitor",
                "conf_type_lc": "",
                "conf_file_lc": "初始化用户",
                "namespace_info": "",
                "description": "我是描述",
                "updated_by": "",
                "created_at": "",
                "updated_at": ""
            },
            "content": {
                "backends_check": "{\"check\": \"YES\"}",
                "conn_log": "{\"check\": \"YES\",\"expire_days\": \"1\",\"max_rows\": \"20000\",\"max_size\": \"2G\"}",
                "disk_os_space": "{\"check\": \"YES\",\"dba_used_percent\": \"90%\",\"percent_value_pre\": \"91\",\"percent_valve\": \"94\"}",
                "proxy_log": "{\"check\": \"YES\"}",
                "proxy_progress": "{\"check\": \"YES\",\"restart\": \"YES\"}",
                "proxy_state": "{\"check\": \"YES\"}",
                "warn_level.conn_log_check": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"2\",\"repeat\": \"1\",\"unimportance_time\": \"0 0\"}",
                "warn_level.conn_log_switch_check": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"3\",\"repeat\": \"1\",\"unimportance_time\": \"0 0\"}",
                "warn_level.db_agent_check_0": "{\"Triggering_warning\": \"3\",\"callup_script\": \"null\",\"level\": \"0\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.db_agent_check_1": "{\"Triggering_warning\": \"3\",\"callup_script\": \"null\",\"level\": \"1\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.db_agent_check_5": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"5\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.disk_os_space": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"0\",\"repeat\": \"6\",\"unimportance_time\": \"0 0\"}",
                "warn_level.disk_os_space_1": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"1\",\"repeat\": \"6\",\"unimportance_time\": \"0 0\"}",
                "warn_level.disk_os_space_pre": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"3\",\"repeat\": \"6\",\"unimportance_time\": \"0 0\"}",
                "warn_level.monitor_center_check": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"3\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.proxy_backends_check": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"1\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.proxy_connection": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"0\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.proxy_log_content_error": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"1\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.proxy_log_content_warn": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"3\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.proxy_log_exit_check": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"3\",\"repeat\": \"2\",\"unimportance_time\": \"0 0\"}",
                "warn_level.proxy_progress_0": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"0\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.proxy_progress_3": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"3\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.proxy_state": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"0\",\"repeat\": \"0\",\"unimportance_time\": \"0 0\"}",
                "warn_level.tokudb_space": "{\"Triggering_warning\": \"0\",\"callup_script\": \"null\",\"level\": \"1\",\"repeat\": \"3\",\"unimportance_time\": \"0 0\"}"
            }
        },
        {
            "bk_biz_id": "0",
            "level_name": "plat",
            "level_value": "0",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "MysqlProxyMonitor",
                "conf_file": "warn_receiver",
                "conf_type_lc": "",
                "conf_file_lc": "",
                "namespace_info": "",
                "description": "",
                "updated_by": "",
                "created_at": "",
                "updated_at": ""
            },
            "content": {
                "warn_receiver": "{\"app\":\"{{}}\", \"db_cat\":\"{{}}\", \"duty_person\":\"{{}}\", \"mail_to\":\"{{}}\", \"domainurl\":\"http://127.0.0.1/\", \"sms_to\":\"\"}"
            }
        },
        {
            "bk_biz_id": "0",
            "level_name": "plat",
            "level_value": "0",
            "conf_file_info": {
                "namespace": "tendbha",
                "conf_type": "MysqlProxyMonitor",
                "conf_file": "xml_server",
                "conf_type_lc": "",
                "conf_file_lc": "",
                "namespace_info": "",
                "description": "",
                "updated_by": "",
                "created_at": "",
                "updated_at": ""
            },
            "content": {
                "xml_server": "{\"ips\":\"\"}"
            }
        }
    ],
    "host": "127.0.0.1",
    "ports": [
        10000
    ]
    }
}
```