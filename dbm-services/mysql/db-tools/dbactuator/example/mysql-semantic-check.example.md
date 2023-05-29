## 运行语义检查 
> dbactuator mysql semantic-check

### payload 
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
        "host":"127.0.0.1",
	    "port":3306,
		"schemafile": "/data/install/schema.sql",
		"remote_host": "127.0.0.1",
		"remote_port": 20000,
		"execute_objects": [
            {
                "sql_file": "/data/install/test.sql",
				"ignore_dbnames": [],
                "dbnames": [
                    "test"
                ]
            }
        ]
  }
}
``` 

## 清理语义检查实例
> dbactuator mysql semantic-check --clean 