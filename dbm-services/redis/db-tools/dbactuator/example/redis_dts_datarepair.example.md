### redis_dts_datacheck
bk-dbmon安装:
```sh
./dbactuator_redis  --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_dts_datarepair"  --payload='{{payload_base64}}'
```

dts_type是迁移类型,有四个值:
- one_app_diff_cluster: 一个业务下的不同集群间迁移
- diff_app_diff_cluster: 不同业务下的不同集群间迁移
- sync_to_other_system: 同步到其他系统,如迁移到腾讯云
- user_built_to_dbm: 用户自建redis到dbm系统

原始payload:
```json
{
    "pkg":"dbtools.tar.gz",
    "pkg_md5":"ced0fa280c63cb31536fefc1845f3ff0",
    "bk_biz_id":"testapp",
    "dts_type":"one_app_diff_cluster",
    "src_redis_ip":"127.0.0.1", //源redis信息
    "src_redis_port_segmentlist":[
        {
            "port":30000,
            "seg_start":-1,
            "seg_end":-1
        }
    ],
    "src_hash_tag":false, //是否开启hash_tag
    "src_redis_password":"xxxxx", //是redis的密码,非srcCluster proxy得密码
    "src_cluster_addr":"tendisx.aaaa.testapp.db:50000", 
    "dst_cluster_addr":"tendisx.bbbb.testapp.db:50000", //目的集群addr
    "dst_cluster_password":"yyyy", //目的集群proxy密码 
    "key_white_regex":"*",
    "key_black_regex":""
}
```