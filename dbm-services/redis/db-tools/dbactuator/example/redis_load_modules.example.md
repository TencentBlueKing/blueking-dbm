### redis load modules
redis加载modules
`./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_load_modules" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'`

`--data_dir`、`--backup_dir` 可以留空.  

前置工作:  
- 将`redis_modules.tar.gz`下载到`/data/install`目录下;  


原始payload
```json
{
    "redis_modules_pkg":{
        "pkg":"redis_modules.tar.gz",
        "pkg_md5":"90f93cd47679fb4509af4c0c5f377be0"
    },
    "ip":"a.a.a.a",
    "ports":[30000,30001,30002],
    "password":"xxx",
    "load_modules_detail":[
        {"major_version": "Redis-6", "module_name": "redisbloom", "so_file": "redisbloom-2.6.13.so"},
        {"major_version": "Redis-6", "module_name": "redisjson", "so_file": "librejson-2.6.6.so"}
    ]
}
```