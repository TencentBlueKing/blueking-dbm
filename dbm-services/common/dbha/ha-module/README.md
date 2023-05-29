# bk-dbha
DBHA是腾讯互娱DB的一套高可用解决方案。原高可用组件DBHA使用perl语言编写，且存在部署、裁撤复杂等诸多问题，本项目用golang语言对DBHA进行了重构
，解决了原DBHA存在的一系列问题，提升了其拓展性，目前主要服务业bk-dbm项目。

## 特性
- 高性能轻量级
- 部署简易
- 动态扩缩容
- 组件自身高可用
- 支持多DB类型
- 机器级别切换


## 编译
要求go1.14+
```
$ go build dbha.go
```

## 部署

DBHA包含Agent和GM两个组件，Agent用于探测实例并上报，GM用于汇总探测信息并做决策和切换。

DBHA部署还需要一个HADB服务，用于记录和操作DBHA元数据相关信息。

### Agent
Agent负责探测所在城市的所有DB实例，并跨城上报探测信息。Agent实例数可以根据所在城市DB实例个数任意进行扩缩容，只需要部署增加或减少一个实例即可。
```
./dbha -type=agent -config_file=/conf/agent.yaml -log_file=/log/dbha.log
```


### GM
GM用于接受来自所有地区的Agent信息。由于Agent跨城上报的特点，建议至少需要两个实例，部署在任意两个城市。
```
$ ./dbha -type=gm -config_file=/conf/gm.yaml -log_file=/log/dbha.log
```

## 配置文件
配置文件采用yaml语法，同时分为Agent和GM两套配置。

### Agent
```
type: "agent"
active_cluster_type: [
  "tendbha:backend"
]
id: "12345"
city: "123"
campus: "坪山"
instance_timeout: 900
db:
  reporter_interval: 60
mysql:
  user: "root"
  pass: "123"
  timeout: 10
ssh:
  port: 36000
  user: "root"
  pass: "xxx"
  dest: "agent"
  timeout: 10
HADB:
  host: "xxx"
  port: 40000
  timeout: 10
CMDB:
  host: "127.0.0.1"
  port: 3306
  timeout: 10
```
- type：DBHA类型，agent或gm
- active_cluster_type：所探测的DB类型，为数组类型，可同时探测多种DB类型，采用`(cluster_type, machine_type)`作为二元组表明一种DB类型，写法为`cluster_type:machine_type`
- id：唯一标识
- city：cc中的城市id
- campus：cc中的园区id
- instance_timeout：agent获取gm和db信息的时间间隔
- db.reporter_interval：db实例探测信息给hadb的时间间隔
- mysql.user：探测所需mysql用户
- mysql.pass：探测所需mysql用户的密码
- mysql.timeout：探测mysql的超时时间
- ssh.port：ssh探测所需端口号
- ssh.user：ssh探测所需用户
- ssh.pass：ssh探测用户所需密码
- ssh.dest：执行ssh探测的角色
- ssh.timeout：ssh探测的超时时间
- HADB.host：访问HADB的域名
- HADB.port：访问HADB的端口号
- HADB.timeout：访问HADB的超时时间
- CMDB.host：访问CMDB的域名
- CMDB.port：访问CMDB的端口号
- CMDB.timeout：访问CMDB的超时时间

### GM
```
type: "gm"
id: "12345"
city: "123"
campus: "浦东"
db:
  reporter_interval: 60
mysql:
  user: "dbha"
  pass: "xxx"
  proxy_user: "proxy"
  proxy_pass: "xxx"
  timeout: 10
ssh:
  port: 36000
  user: "dba"
  pass: "xxx"
  dest: "agent"
  timeout: 10
HADB:
  host: "127.0.0.1"
  port: 3306
  timeout: 10
CMDB:
  host: "127.0.0.1"
  port: 3306
  timeout: 10
GDM:
  liston_port: 50000
  dup_expire: 600
  scan_interval: 1
GMM:
GQA:
  idc_cache_expire: 300
  single_switch_idc: 50
  single_switch_interval: 86400
  single_switch_limit:  48
  all_host_switch_limit:  150
  all_switch_interval:  7200
GCM:
  allowed_checksum_max_offset: 2
  allowed_slave_delay_max: 600
  allowed_time_delay_max: 300
  exec_slow_kbytes: 0
```
部分参数与Agent同名参数含义相同
- mysql.proxy_user：切换mysql时其proxy管理端口用户
- mysql.proxy_pass：切换mysql时其proxy管理用户密码
- GDM.liston_port：GM监听端口
- GDM.dup_expire：GDM缓存实例的时间
- GDM.scan_interval：GDM扫描实例的时间间隔
- GQA.idc_cache_expire：GQA查询IDC信息的缓存时间
- GQA.single_switch_idc：一分钟内单个IDC切换阈值
- GQA.single_switch_interval：GQA获取该实例多少时间内的切换次数
- GQA.single_switch_limit：该实例切换次数阈值
- GQA.all_host_switch_limit：DBHA切换次数阈值
- GQA.all_switch_interval：GQA获取DBHA多少时间内的切换次数
- GCM.allowed_checksum_max_offset：允许多少表的crc32值不相等
- GCM.allowed_slave_delay_max：更新master_slave_check的延迟阈值
- GCM.allowed_time_delay_max：master和slave之间的同步时间延迟阈值
- GCM.exec_slow_kbytes：slave落后master的数据大小阈值

## 镜像部署
### 镜像制作

```bash
docker build . -t mirrors.tencent.com/sccmsp/bkm-dbha:${version}
```

### 测试

```bash
docker run -it --name dbha -d mirrors.tencent.com/sccmsp/bkm-dbha:${version}  bash -c "sleep 3600"
```

## helm部署
```bash
cd bk-dbha
helm install . -g
helm list
```
