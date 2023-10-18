# 使用
* riak-monitor被mysql-crond调起
* 必须先部署 `mysql-crond`
* 配置文件分为 _runtime_ 配置 和 监控项配置
* _runtime_ 配置需要作为命令行参数传入, 如 `mysql-crond -c runtime.yaml`
* 监控项配置在 _runtime_ 配置中指定，相关配置文件示例见”示例文件“
* 前台启动
  * 示例：
    * /data/monitor/riak-crond/mysql-crond -c /data/monitor/riak-crond/runtime.yaml
* 后台执行
  * 示例：
    * /data/monitor/riak-crond/start.sh -c /data/monitor/riak-crond/runtime.yaml
      * cat start.sh 
      * SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
        cd $SCRIPT_DIR && nohup ./mysql-crond ${@:1} &

* 查看定时任务： 
  * curl http://xxx:xxx/entries
* 关闭定时任务：
  * curl http://xxx:xxx/quit

## 硬编码项
目前有两个硬编码项
1. 执行心跳
2. 连接 _DB_ 失败
* 如果监控项配置中缺少这两项, 会被自动添加
* 以 `hardcode-run` 子命令运行


# 监控项配置
```go
type MonitorItem struct {
	Name        string   `yaml:"name" validate:"required"`
	Enable      *bool    `yaml:"enable" validate:"required"`
	Schedule    *string  `yaml:"schedule"`
	MachineType string   `yaml:"machine_type"`
}
```

* `name`: 监控项名称, 对应蓝鲸监控平台的事件
* `enable`: 是否启用
* `schedule`: 可选, 在 _runtime_ 配置中有默认值, 不建议修改
* `machine_type`: 基于机器类型的过滤

## 分组
在注册 `mysql-crond entry` 时, 会按照 _schedule_ 把所有监控项分组注册

# 开发
1. 在 `items_collect` 中添加监控项目录, 如 _some_new_item_
2. 在 _some_new_item_ 中实现 `monitor_item_interface.MonitorItemInterface`
3. 同时还要提供 
   * `func New(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface` 
   * `func Register() (string, monitor_item_interface.MonitorItemConstructorFuncType)`
4. 在 `items_collect.init` 中注册新增的监控项   
5. 把新增监控项的相关配置已经添加到 _items-config.yaml_ 中


# 监控项

| 监控项                      |调度计划| 机器类型           | 实例角色            |级别| 说明                          |自定义|
|--------------------------|-----|----------------|-----------------|-----|-----------------------------|-----|
| riak-err-notice          |@every 1m| riak           |                 | 预警           | 预警错误日志                      |schedule, enable
| riak-db-up                    |@every 10s| backend, proxy |                 | 致命           | db 连通性. 硬编码, 不可配置, 无需录入配置系统 |enable
| riak_monitor_heart_beat |@every 10s| riak           |                 | 致命             | 监控心跳. 硬编码, 不可配置, 无需录入配置系统   |enable
| riak-load-health |@every 1m| riak           |                 | 致命             | 检查负载与响应情况                   |enable
| riak-ring-status |@every 10s| riak           |                 | 致命             | 检查ring status, 发现集群中所有的故障节点 |enable

  
## 示例文件：
请在Editor模式下查看
1. mysql-crond的runtime.yaml示例：
ip: xxx
port: xxx
bk_cloud_id: 0
bk_monitor_beat:
custom_event:
bk_data_id: xxx
access_token: xxx
report_type: agent
message_kind: event
custom_metrics:
bk_data_id: xxx
access_token: xxx
report_type: agent
message_kind: timeseries
beat_path: xxx
agent_address: xxx
log:
console: false
log_file_dir: /data/monitor/riak-crond
debug: false
source: true
json: true
pid_path: /data/monitor/riak-crond
jobs_user: root
jobs_config: /data/monitor/riak-crond/jobs-config.yaml


2. mysql-crond的jobs-config.yaml示例：
- name: riak-err-notice@every 1m
  enable: true
  command: /data/monitor/riak-monitor/riak-monitor
  args:
    - run
    - --items
    - riak-err-notice
    - -c
    - /data/monitor/riak-monitor/runtime.yaml
      schedule: '@every 1m'
      creator: admin
      work_dir: ""
- name: riak-load-health@every 1m
  enable: true
  command: /data/monitor/riak-monitor/riak-monitor
  args:
    - run
    - --items
    - riak-load-health
    - -c
    - /data/monitor/riak-monitor/runtime.yaml
      schedule: '@every 1m'
      creator: admin
      work_dir: ""
- name: riak-ring-status@every 10s
  enable: true
  command: /data/monitor/riak-monitor/riak-monitor
  args:
    - run
    - --items
    - riak-ring-status
    - -c
    - /data/monitor/riak-monitor/runtime.yaml
      schedule: '@every 10s'
      creator: admin
      work_dir: ""
- name: riak-monitor-hardcode@every 10s
  enable: true
  command: /data/monitor/riak-monitor/riak-monitor
  args:
    - hardcode-run
    - --items
    - riak-db-up,riak_monitor_heart_beat
    - -c
    - /data/monitor/riak-monitor/runtime.yaml
      schedule: '@every 10s'
      creator: admin
      work_dir: ""
      bk_biz_id: xxx

3. riak-monitor的runtime.yaml示例：
bk_biz_id: xxx
ip: xxx
port: xxx
bk_instance_id: xxx
immute_domain: xxx
machine_type: riak
bk_cloud_id: 0
log:
console: true
log_file_dir: /data/monitor/riak-monitor/logs
debug: true
source: true
json: false
api_url: xxx
items_config_file: /data/monitor/riak-monitor/items-config.yaml
interact_timeout: 2s
default_schedule: '@every 1m'

4. riak-monitor的items-config.yaml示例：
- name: riak-err-notice
  enable: true
  schedule: '@every 1m'
  machine_type:
    - riak
- name: riak-load-health
  enable: true
  schedule: '@every 1m'
  machine_type:
    - riak
- name: riak-ring-status
  enable: true
  schedule: '@every 10s'
  machine_type:
    - riak
- name: riak-db-up
  enable: true
  schedule: '@every 10s'
  machine_type:
    - riak
- name: riak_monitor_heart_beat
  enable: true
  schedule: '@every 10s'
  machine_type:
    - riak
