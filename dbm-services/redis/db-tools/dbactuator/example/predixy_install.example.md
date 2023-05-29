# predixy_install
## 安装predixy
`./dbactuator_redis  
--uid={{uid}}
--root_id={{root_id}}
--node_id={{node_id}}
--version_id={{version_id}}
--atom-job-list="predixy_install"
--payload='{{payload_base64}}'`

## 前置工作:
- 先运行 `./dbactuator_redis --atom-job-list="sysinit"`
- 将`predixy-1.0.5.tar.gz`下载到`/data/install`目录下;


##原始payload
```json
{
  "ip":"127.0.0.1",
  "port":50000,
  "predixypasswd":"xxxxx",
  "redispasswd":"xxxxx",
  "predixyadminpasswd":"xxxxx",
  "servers":[
    "127.0.0.1:11",
    "2.2.2.2:11"
  ],
  "dbconfig":{
    "workerthreads":"8",
    "clienttimeout":"0",
    "RefreshInterval":"1",
    "serverfailurelimit":"10",
    "serverretrytimeout":"1",
    "servertimeout":"0",
    "keepalive":"0",
    "slowloglogslowerthan":"10000",
    "slowlogmaxlen":"1024"
  },
  "mediapkg":{
    "pkg":"predixy-1.4.0.tar.gz",
    "pkg_md5":"9a863ce100bfe6138523d046c068f49c"
  }
}
```