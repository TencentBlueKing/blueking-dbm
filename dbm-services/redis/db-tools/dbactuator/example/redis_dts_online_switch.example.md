### redis_dts_online_switch
dts 在线切换:
```
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_dts_online_switch" --payload='{{payload_base64}}'
```

原始payload
```json
{
    "dst_proxy_pkg":{
        "pkg":"predixy-1.4.0.tar.gz",
        "pkg_md5":"24aba4a96dcf7f8581d2fde89d062455"
    },
    "dts_bill_id":1111,
    "src_proxy_ip": "xx.xx.xx.xx",
    "src_proxy_port":50000,
    "src_proxy_password":"passxxxx",
    "src_cluster_type":"TwemproxyRedisInstance",
    "dst_proxy_ip":"yy.yy.yy.yy",
    "dst_proxy_port":50100,
    "dst_proxy_password":"passyyyy",
    "dst_cluster_type":"PredixyTendisplusCluster",
    "dst_redis_ip":"a.a.a.a",
    "dst_redis_port":30000,
    "dst_proxy_config_content":"
Bind yy.yy.yy.yy:50100
WorkerThreads 8
ClientTimeout 0
Authority {
    Auth \"passyyyy\" {
        Mode write
    }
}
Log /data/predixy/50100/logs/log
LogRotate 1d
ClusterServerPool {
    Password xxxxxx
    RefreshInterval 1
    ServerFailureLimit 10 
    ServerRetryTimeout 1
    ServerTimeout 0
    KeepAlive 0
    Servers {
        + a.a.a.a:30000
    + b.b.b.b:30000


    }
}
LatencyMonitor all {
        Commands {
                + all
        }
        TimeSpan {
                + 100
                + 500
                + 1000
                + 5000
                + 10000
        }
}
    "
}
```