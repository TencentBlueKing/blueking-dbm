### redis install
安装redis  
`./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_install" --data_dir=/path/to/data  --backup_dir=/path/to/backup --payload='{{payload_base64}}'`

`--data_dir`、`--backup_dir` 可以留空.  

前置工作:  
- 先运行 `./dbactuator_redis --atom-job-list="sysinit"`
- 将`redis-6.2.7.tar.gz`下载到`/data/install`目录下;  

原始payload
```json
{
    "pkg":"redis-6.2.7.tar.gz",
    "pkg_md5":"1fc9e5c3a044ce523844a6f2717e5ac3",
    "dbtoolspkg":{
        "pkg":"dbtools.tar.gz",
        "pkg_md5":"334cf6e3b84d371325052d961584d5aa"
    },
    "data_dirs":[], // 优先尝试用 /data1/ /data/作为数据保存目录,而后测试 data_dirs 中目录是否满足,满足则可用作数据目录
    "ip":"127.0.0.1",
    "ports":[], //端口不连续
    "start_port":30000, // 端口连续,起始端口
    "inst_num":3, //实例个数
    "password":"xxx",
    "databases":2,
    "db_type":"TwemproxyRedisInstance",
    "maxmemory":536870912,
    "redis_conf_configs":{
        "activerehashing":"yes",
        "always-show-logo":"yes",
        "aof-load-truncated":"yes",
        "aof-rewrite-incremental-fsync":"yes",
        "aof-use-rdb-preamble":"no",
        "appendfilename":"appendonly.aof",
        "appendfsync":"everysec",
        "appendonly":"no",
        "auto-aof-rewrite-min-size":"64mb",
        "auto-aof-rewrite-percentage":"100",
        "bind":"{{address}} 127.0.0.1",
        "client-output-buffer-limit":"normal 0 0 0 \n client-output-buffer-limit slave 2048mb 2048mb 300 \n client-output-buffer-limit pubsub 32mb 8mb 60",
        "cluster-config-file":"nodes.conf",
        "cluster-enabled":"{{cluster_enabled}}",
        "cluster-node-timeout":"15000",
        "daemonize":"yes",
        "databases":"{{databases}}",
        "dbfilename":"dump.rdb",
        "dir":"{{redis_data_dir}}/data",
        "hash-max-ziplist-entries":"512",
        "hash-max-ziplist-value":"64",
        "hll-sparse-max-bytes":"3000",
        "hz":"10",
        "lazyfree-lazy-eviction":"yes",
        "lazyfree-lazy-expire":"yes",
        "lazyfree-lazy-server-del":"yes",
        "list-compress-depth":"0",
        "list-max-ziplist-size":"-2",
        "logfile":"{{redis_data_dir}}/redis.log",
        "loglevel":"notice",
        "lua-time-limit":"5000",
        "maxclients":"180000",
        "maxmemory":"{{maxmemory}}",
        "maxmemory-policy":"noeviction",
        "no-appendfsync-on-rewrite":"yes",
        "pidfile":"{{redis_data_dir}}/redis.pid",
        "port":"{{port}}",
        "protected-mode":"yes",
        "rdbchecksum":"yes",
        "rdbcompression":"yes",
        "rename-command":"flushall cleanall \n rename-command config confxx \n rename-command flushdb cleandb \n rename-command debug nobug \n rename-command keys mykeys",
        "repl-diskless-sync":"no",
        "requirepass":"{{password}}",
        "save":"",
        "slave-lazy-flush":"yes",
        "slave-priority":"100",
        "slave-read-only":"yes",
        "slave-serve-stale-data":"yes",
        "slowlog-log-slower-than":"10000",
        "slowlog-max-len":"256",
        "stop-writes-on-bgsave-error":"yes",
        "supervised":"no",
        "tcp-backlog":"511",
        "tcp-keepalive":"300",
        "timeout":"0",
        "zset-max-ziplist-entries":"128",
        "zset-max-ziplist-value":"64"
    },
}
```