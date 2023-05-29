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
### 二进制编译
```
make build
```
### 编辑镜像
```
make image VERSION=x.x.x
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
配置文件采用yaml语法，主要由Agent，GM和其他公共group组成。
实际部署时，公共group必须配置指定，

### 公共配置
```yaml
#用于指定日志记录、归档方式
log_conf:
  log_path: "./log"
  log_level: "LOG_DEBUG"
  log_maxsize: 1024
  log_maxbackups: 5
  log_maxage: 30
  log_compress: true

#DB配置相关
db_conf:
  #用于指定hadb api的访问方式
  hadb:
    host: "hadb访问地址"
    port: 访问端口
    timeout: 10
    url_pre: "url前缀，非必须指定"
    bk_conf:
      bk_token: "蓝鲸API访问token"

  #用于指定cmdb api的访问方式
  cmdb:
    host: "cmdb访问地址"
    port: 80
    url_pre: "url前缀，非必须指定"
    timeout: 10
    bk_conf:
      bk_token: "蓝鲸API访问token"
  #用于指定mysql实例的探测配置
  mysql:
    user: "xxxxxx"
    pass: "xxxxxx"
    proxy_user: "xxxxxx"
    proxy_pass: "xxxxxx"
    timeout: 10
  #用于指定redis实例的探测配置
  redis:
    timeout: 10

#名字服务相关
name_services:
  #dns配置
  dns_conf:
    host: "dns访问地址"
    port: 80
    url_pre: "url前缀，非必须指定"
    timeout: 10
    bk_conf:
      bk_token: "蓝鲸API访问token"
  #远程配置服务
  remote_conf:
    host: "远程服务访问地址"
    port: 80
    url_pre: "url前缀，非必须指定"
    timeout: 10
    bk_conf:
      bk_token: "蓝鲸API访问token"
  #北极星服务配置
  polaris_conf:
    host: "北极星访问地址"
    port: 80
    user: "nouser"
    pass: "nopasswd"
    url_pre: "url前缀，非必须指定"
    timeout: 10
  clb_conf:
    host: http://bk-dbm-addons-db-name-service/
    port: 80
    user: "nouser"
    pass: "nopasswd"
    url_pre: "/api/nameservice/clb"
    timeout: 10
#统一告警配置
monitor:
  bk_data_id: 告警ID
  access_token: "访问token"
  beat_path: "告警程序路径"
  agent_address: "告警配置地址"
  local_ip: "本地IP"
#ssh探测配置
ssh:
  port: 36000
  user: "xxxxxx"
  pass: "xxxxx"
  dest: "agent"
  timeout: 10
```

### Agent
```
agent_conf:
  active_db_type: [
    "tendbha",
    "tendbcluster",
  ]
  city_id: 1
  cloud_id: 0
  campus: "深圳"
  fetch_interval: 120
  reporter_interval: 120
  local_ip: "agent本机IP"
```
- active_cluster_type：所探测的DB类型，为数组类型，可同时探测多种DB类型
  目前合法的为：tendbha,tendbcluster,TwemproxyRedisInstance,PredixyTendisplusCluster
- city_id：cc中的城市id
- campus：cc中的城市名

### GM
```
gm_conf:
  city_id: 1
  cloud_id: 0
  campus: "深圳"
  liston_port: GM运行端口
  report_interval: 60
  local_ip: "GM本机IP"
  GDM:
    dup_expire: 600
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
- GDM.liston_port：GM监听端口
- GDM.dup_expire：GDM缓存实例的时间
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
make image
```

### 测试

```bash
docker run -it --name dbha -d mirrors.tencent.com/build/blueking/dbha:${version}  bash -c "sleep 3600"
```

## helm部署
```bash
cd bk-dbha
helm install . -g
helm list
```
