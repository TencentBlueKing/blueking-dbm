# dbactuator hdfs xxx

## hdfs集群部署


### 原始payload
```
{
    "general": {},
    "extend": {
        "host": "127.x.x.x",  --本机IP
        -- 集群配置

        "core-site": {
            "fs.defaultFS": "hdfs://{{cluster_name}}",
            "fs.trash.interval": "1440",
            "io.file.buffer.size": "131072",
            "net.topology.script.file.name": "/data/hadoopenv/hadoop/etc/hadoop/rack-aware.sh"
        },
        "hdfs-site": {...}
        "zoo.cfg": {...}
        "install": {...}
        "cluster_name": "richie-hdfs"
        "http_port": 50070,
        "rpc_port": 9000,  
                             

    }
}

```