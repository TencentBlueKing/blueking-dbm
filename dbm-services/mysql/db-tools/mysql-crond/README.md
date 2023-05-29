# 使用方法

1. 打包 `make linux-pkg VERSION=0.0.4`
   * _VERSION_ 必须给定值, 这个值是设计给蓝盾流水线用的. 人工使用随便给个 _x.y.z_ 形式的就行
2. 命令行参数
   * `-c/--config` 指定运行时参数文件
   * `--without-heart-beat` 关闭心跳, 专门给开发测试用的
3. 测试运行 `sh run_local.sh -c /path_to/runtime.yaml --without-heart-beat` 

* _runtime.yaml_ 部署后几乎不会有变化
* _jobs-config.yaml_ 是任务定义, 可以被 _api_ 影响
  * 所有修改 _jobs_ 的 _api_ 在使用 _permanent=true_ 时会将配置持久化
  * 持久化时原文件会被整个重写, 所有注释全都删除

##  查看注册的任务列表

1. 方法一: http api:
```
curl http://127.0.0.1:9999/entries |jq
```
2. 方法二: list 命令
```
./mysql-crond -c runtime.yaml list
```

# 事件

1. 所有注册的任务执行失败时会自动发送蓝鲸告警通知, 要求是
    * 任务命令必须严格遵守 `0/1 exit code` 的标准 
    * 执行失败时要向 _stderr_ 打印必要的错误信息
2. 所有任务都遵循 `SkipIfStillRunning` 的调度策略
    * 上一轮任务未结束时, 本次调度会跳过, 等待下一次调度
    * 产生这种情况时会发送蓝鲸告警
3. 事件名由 _runtime config_ 中的 _bk_monitor_beat.inner_event_name_ 指定

# 心跳
* 程序本身会默认启动一个 `@every 1m` 的任务发送心跳指标到蓝鲸监控
* 指标名由 _runtime config_ 中的 _bk_monitor_beat.inner_metrics_name_ 指定, 添加对应的监控策略就可以监控任务调度是否正常

# 部署
* 程序部署依赖蓝鲸节点管理, _runtime config_ 由蓝鲸生成
* 初次部署后 _jobs config_ 文件为空
* 初次部署后需要编辑 _jobs config_ 添加 `bk_biz_id, immute_domain, machine_type, role` 信息
* 完成修改 _jobs config_ 后调用 `/config/reload GET` 加载配置

# 配置文件

## 运行时配置 _--config_
```yaml
ip: 127.0.0.1
port: 9999
bk_cloud_id: 0
bk_monitor_beat:
  inner_event_name: mysql_crond_event
  inner_metrics_name: mysql_crond_beat
  custom_event:
    bk_data_id: 542898
    access_token: xxxx
    report_type: agent
    message_kind: event
  custom_metrics:
    bk_data_id: 543957
    access_token: xxxx
    report_type: agent
    message_kind: timeseries
  beat_path: /usr/local/gse_bkte/plugins/bin/bkmonitorbeat
  agent_address: /usr/local/gse_bkte/agent/data/ipc.state.report
log:
    console: true
    log_file_dir: /Users/xfwduke/mysql-crond/logs
    debug: true
    source: true
    json: false
pid_path: /Users/xfwduke/mysql-crond
jobs_user: xfwduke
jobs_config: /Users/xfwduke/mysql-crond/jobs-config.yaml
```

1. `ip` 为本机 _ip_ 地址
2. `port` 为 _mysql-crond http_ 服务监听端口, 服务强制 _bind 127.0.0.1_
3. `log_file_dir, pid_path, jobs_config` 必须为绝对路径
4. `jobs_user` 设置为机器上存在的用户名, 所有任务及日志文件都属于这个用户
5. `custom_event` 为蓝鲸自定义事件配置
   * `bk_data_id, access_token` 按需修改
   * 其他的不要动
6. `custom_metrics` 为蓝鲸自定义指标配置
   * `bk_data_id, access_token` 按需修改
   * 其他的不要动
7. `inner_event_name` 指定本程序内部发送的事件名, 用于监控任务调度是否有延迟
8. `inner_metrics_name` 指定本程序自身的心跳指标名, 用于监控任务调度是否正常


## 任务定义 _--jobs-config_
```yaml
jobs:
    - name: bb
      enable: true
      command: echo
      args:
        - dd
      schedule: '@every 1m'
      creator: ob
      work_dir: ""
bk_biz_id: 404
immute_domain: aaa.bbbb.ccc
machine_type: backend
role: master
```

* `work_dir`: 默认情况下 `mysql-crond` 调度的作业 _cwd_ 是 `mysql-crond` 的所在目录, 在注册作业使用 _cwd_ 时可能会出现异常. 可以使用这个参数指定作业自己的 _cwd_

# _http api_

## `/entries GET` 

返回活跃的任务

### _response_
```json
{
  "entries": []cron.Entry
}
```

```go
type Entry struct {
	ID EntryID
	Schedule Schedule
	Next time.Time
	Prev time.Time
	WrappedJob Job
	Job Job
}
```

`Entry.Job` 是一个 `interface` , 所以实际是自定义的任务类型

```go
type ExternalJob struct {
	Name     string   `yaml:"name" binding:"required" validate:"required"`
	Enable   *bool    `yaml:"enable" binding:"required" validate:"required"`
	Command  string   `yaml:"command" binding:"required" validate:"required"`
	Args     []string `yaml:"args" binding:"required" validate:"required"`
	Schedule string   `yaml:"schedule" binding:"required" validate:"required"`
	Creator  string   `yaml:"creator" binding:"required" validate:"required"`
	WorkDir  string   `yaml:"work_dir" json:"work_dir" form:"work_dir"`
}
```

## `/disabled GET`
返回被停止的任务

### _response_
```json
{
  "jobs": []ExternalJob
}
```

## `/disable POST`

停止处于活跃的任务

### _request_

```json
{
  "name": string,
  "permanent": bool,
}
```

* _name_ : 任务名称
* _permanent_ : 是否持久化到配置文件

### _response_
```json
{
  "entry_id": int
}
```

* _entry_id_ : 成功操作的作业 _id_

## `/resume POST`
恢复被停止的任务

### _request_

```json
{
  "name": string,
  "permanent": bool,
}
```

* _name_ : 任务名称
* _permanent_ : 是否持久化到配置文件

### _response_
```json
{
  "entry_id": int
}
```


## `/pause POST`
暂停处于活跃的任务一段事件, 超时后自动恢复

### _request_
```json
{
  "name": string,
  "duration": time.Duration,
}
```

* _name_ : 任务名称
* _duration_ : _golang_ 形式的 _time.Duration_ 字符串, 如 _1s, 1h30m_

### _response_
```json
{
  "entry_id": int
}
```

* _entry_id_ : 成功操作的作业 _id_



## `/create_or_replace POST`
新增或者替换一个任务的定义


### _request_
```json
{
  "job": {
    "name": string
    "command": string
    "args": []string,
    "schedule": string,
    "creator": string,
    "work_dir": string, # optional
    "enable": bool
  },
  "permanent": bool
}
```

* _job_ : 任务描述
    * _name_ : 任务名称, 全局唯一
    * _command_ : 可以正常运行的命令
    * _args_ : 命令参数列表
    * _schedule_ : 支持秒的调度配置, 如 _@every 2s_ , _@every 1h10m_ , _*/30 * * * * *_
    * _creator_ : 创建人
    * _enable_ : 是否启用
* _permanent_: 是否持久化到配置文件

## `/delete POST`
删除一个任务
### _request_

```json
{
  "name": string,
  "permanent": bool,
}
```

* _name_ : 任务名称
* _permanent_ : 是否持久化到配置文件
### _response_
```json
{
  "entry_id": int
}
```

* 删除的是 _activity_ 任务时为真实 _id_
* 删除的是 _disabled_ 任务时恒为 _0_

## `/beat/event POST`
发送一个自定义事件
### _request_
```json
{
  "name": string
  "content": string
  "dimension": dict[string]:string or int
}
```

* `name`: 自定义事件名称
* `content`: 事件内容
* `dimension`: 附加的维度

默认就强制添加的维度
```go
dimension["bk_biz_id"] = JobsConfig.BkBizId
dimension["bk_cloud_id"] = *RuntimeConfig.BkCloudID
dimension["server_ip"] = RuntimeConfig.Ip
dimension["immute_domain"] = JobsConfig.ImmuteDomain
dimension["machine_type"] = JobsConfig.MachineType

if JobsConfig.Role != nil {
	dimension["role"] = *JobsConfig.Role
}
```

## _response_
无

## `/beat/metrics POST`
发送一个自定义指标
### _request_
```json
{
  "name": string
  "value": int
  "dimension": dict[string]:string or int
}
```

* `name`: 自定义指标名称
* `value`: 指标的值
* `dimension`: 附加的维度

带有和 `/beat/event` 一样的默认维度

### _response_
无

## `/config/jobs-config GET`
返回配置的 _jobs config file_ 的路径

### _response_
```json
{
    "path": string
}
```

## `/config/reload GET`
重新加载 _jobs config_ , 用于人肉修改配置文件后的加载

# _sdk_

```go
import ma "dbm-services/mysql/db-tools/mysql-crond/api"
```

1. 用 `func NewManager(apiUrl string) *Manager` 获得管理器
2. 提供了所有的 _http api_ 操作
3. _entries_ 的返回是
    ```go
    type SimpleEntry struct {
      ID  int                `json:"ID"`
      Job config.ExternalJob `json:"Job"`
    }
    ```
   比 _http api_ 要简单