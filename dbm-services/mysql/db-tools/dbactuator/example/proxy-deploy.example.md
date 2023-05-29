# dbactuator proxy deploy 
安装proxy  
`dbactuator proxy deploy -u xx -n xx -p <base64(payload)> `   
前置工作
-  先运行 dbactuator sys init
-  将mysql-proxy-0.82.9.tar.gz 下载到 /data/install

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
        }
    },
    "extend":{
    "host":"127.0.0.1",
    "pkg": "mysql-proxy-0.82.9.tar.gz",
    "pkg_md5": "7e42a8c69c2d296d379252cdca280afc",
"start_port": 10000,
    "inst_num": 1,
    "proxy_configs": {
        "mysql-proxy": {
            "ignore-user": "MONITOR,proxy","conn_log": "true","daemon": "true","keepalive": "true","query_response_time_stats": "true","event-threads": "7","log-level": "warning","plugins": "admin, proxy","proxy-address": "127.0.0.1:3306"
        }
    }
  }
}
```