# dbactuator mysql change-master 
安装mysql  
`dbactuator mysql change-master -u xx -n xx -p <base64(payload)> `   
前置工作
-  安装好两组mysql实例

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
		"host": "127.0.0.1",
		"port": 20000,
		"master_host": "127.0.0.2",
		"master_port": 20000,
		"is_gtid": false,
		"bin_file": "binlog20000.000003",
		"bin_position": 2362,
		"max_tolerate_delay": 10,
		"force": false
    }
}
```