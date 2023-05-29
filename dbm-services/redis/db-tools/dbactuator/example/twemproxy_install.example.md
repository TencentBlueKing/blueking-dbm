# twemproxy install
## 安装redis  
`./dbactuator_redis  
--uid={{uid}} 
--root_id={{root_id}} 
--node_id={{node_id}} 
--version_id={{version_id}} 
--atom-job-list="twemproxy_install"
--payload='{{payload_base64}}'`

## 前置工作:  
- 先运行 `./dbactuator_redis --atom-job-list="twemproxy_install"`
- 将`twemproxy-0.4.1-v22.tar.gz`下载到`/data/install`目录下;

## 原始payload
[twemproxy_install.json] (./twemproxy_install.json)

## 目录与文件
- binDir : /usr/local/twemproxy -> /usr/local/twemproxy-0.4.1-v22
- dataDir : /data/twemproxy-0.2.4/$port
- configFile : /data/twemproxy-0.2.4/52006/nutcracker.52006.yml
```
 cat /data/twemproxy-0.2.4/52006/nutcracker.52006.yml
# twemproxy instance conf of 1.1.1.2 52006
nosqlproxy:
  backlog : 512
  redis_password : xxxxx
  redis : true
  distribution : modhash
  hash : fnv1a_64
  slowms : 1000000
  password : xxxxx
  server_failure_limit : 3
  listen : 1.1.1.2:52006
  auto_eject_hosts : false
  preconnect : false
  server_retry_timeout : 2000
  server_connections : 1
  servers:
  - 127.0.0.1:30000:1 redistest 0-69999 1

```