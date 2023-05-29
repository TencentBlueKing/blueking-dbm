



# 使用
* 必须先部署 `mysql-crond`
* 配置文件分为 _runtime_ 配置 和 监控项配置
* _runtime_ 配置需要作为命令行参数传入, 如 `mysql-monitor -c runtime.yaml`
* 监控项配置在 _runtime_ 配置中指定

## _reschedule_
* 部署监控后, 执行 `mysql-monitor -c runtime.yaml reschedule --staff who-r-u` 来注册 `mysql-crond entry`
* 任何时候修改了监控项配置都需要 `reschedule`

## _clean_
* 执行 `mysql-monitor -c runtime.yaml clean` 会删除所有相关的 `mysql-crond entry`

* 会触发 `监控心跳丢失` 的告警
* 一般只用于下架场景
* 如果临时停止监控需求, 用下面的 `disable-all`

## _disable-all_
`mysql-monitor disable-all -c monitor-config_20000.yaml --staff somebody --with-db-up`
* 保留 `监控心跳`
* 停掉包括`db-up` 在内的所有监控项

如果不使用 `--with-db-up`, 则会保留 `db-up` 监控项

不修改任何配置文件, _disable_ 不会持久化, 可以随时使用上面提到的 _reschedule_ 恢复回来



## 硬编码项
目前有两个硬编码项
1. 执行心跳
2. 连接 _DB_ 失败

* 如果监控项配置中缺少这两项, 会被自动添加
* `reschedule` 后会自动注册 `mysql-crond entry`
* `schedule` 不可修改, 即使修改了也会忽略
* `enable` 可以修改
* 以 `hardcode-run` 子命令运行


# 监控项配置

## 语义
```yaml
- name: character_consistency
  enable: true
  machine_type: backend
  role: ["master", "slave", "repeater"]
  schedule: "1 1 13 * * 1"
- name: routine-definer
  enable: true
  machine_type: backend
  role: ["master", "slave", "repeater"]
- name: master-slave-heartbeat
  enable: true
  machine_type: backend  
```

```go
type MonitorItem struct {
	Name        string   `yaml:"name" validate:"required"`
	Enable      *bool    `yaml:"enable" validate:"required"`
	Schedule    *string  `yaml:"schedule"`
	MachineType string   `yaml:"machine_type"`
	Role        []string `yaml:"role"`
}
```

* `name`: 监控项名称, 对应蓝鲸监控平台的事件
* `enable`: 是否启用
* `schedule`: 可选, 在 _runtime_ 配置中有默认值, 不建议修改
* `machine_type`: 基于机器类型的过滤
* `role`: 基于角色的过滤, 如未提供则对应机器类型的所有角色都可用

## 分组
在注册 `mysql-crond entry` 时, 会按照 _schedule_ 把所有监控项分组注册
比如下面这样子
```json
{
  "entries": [
    {
      "ID": 5,
      "Job": {
        "Name": "mysql-monitor-20000-@every 5m",
        "Enable": true,
        "Command": "/home/mysql/mysql-monitor/mysql-monitor",
        "Args": [
          "run",
          "--items",
          "routine-definer,view-definer,trigger-definer,engine,ext3_check,master_slave_heartbeat",
          "-c",
          "/home/mysql/mysql-monitor/monitor-config_20000.yaml"
        ],
        "Schedule": "@every 5m",
        "Creator": "xxx"
      }
    },
    {
      "ID": 6,
      "Job": {
        "Name": "mysql-monitor-20000-hardcode",
        "Enable": true,
        "Command": "/home/mysql/mysql-monitor/mysql-monitor",
        "Args": [
          "hardcode-run",
          "--items",
          "db-up,mysql-monitor-heart-beat",
          "-c",
          "/home/mysql/mysql-monitor/monitor-config_20000.yaml"
        ],
        "Schedule": "@every 5m",
        "Creator": "xxx"
      }
    },
    {
      "ID": 4,
      "Job": {
        "Name": "mysql-monitor-20000-1 1 13 * * 1",
        "Enable": true,
        "Command": "/home/mysql/mysql-monitor/mysql-monitor",
        "Args": [
          "run",
          "--items",
          "character_consistency",
          "-c",
          "/home/mysql/mysql-monitor/monitor-config_20000.yaml"
        ],
        "Schedule": "1 1 13 * * 1",
        "Creator": "xxx"
      }
    }
  ]
}
```

# 开发

1. 在 `items_collect` 中添加监控项目录, 如 _some_new_item_
2. 在 _some_new_item_ 中实现 `monitor_item_interface.MonitorItemInterface`
3. 同时还要提供 
   * `func New(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface` 
   * `func Register() (string, monitor_item_interface.MonitorItemConstructorFuncType)`
4. 在 `items_collect.init` 中注册新增的监控项   
5. 把新增监控项的相关配置已经添加到 _items-config.yaml_ 中

## _monitor_item_interface.ConnectionCollect_

```go
type ConnectionCollect struct {
	MySqlDB      *sqlx.DB
	ProxyDB      *sqlx.DB
	ProxyAdminDB *sqlx.DB
}
```
这是一个连接句柄的集合, _monitor_ 程序会按照 _runtime_config_ 中 _machine_type_ 的值初始化对应的成员
* _backend_: 初始化 `MySQLDB`
* _proxy_: 初始化 `ProxyDB` 和 `ProxyAdminDB` , 其中 `ProxyAdminDB` 的连接端口为 `服务端口 + 1000`

## _MonitorItemInterface::Run() (msg string, err error)_

* `msg != nil && err == nil` : 监控项顺利, 发现了需要上报的事件. 
* `err!=nil`: 监控项执行异常

这两种情况都会生成上报的事件

# 监控项

|监控项|调度计划|机器类型| 实例角色            |级别|说明|自定义|
|-----|-----|-----|-----------------|-----|-----|-----|
|slave-status|@every 1m|backend| repeater, slave |致命|mysql replicate 同步状态|schedule, enable
|character-consistency|0 0 14 \* \* 1|backend|                 |预警|mysqld 字符集和 database 默认字符集一致性|schedule, enable
|ext3-check|0 0 16 \* \* 1|backend|                 | 致命              |文件系统为 ext3 是否有 1T+ 的数据文件|schedule, enable
|rotate-slowlog|0 55 23 \* \* \*|backend|                 | 无               |慢查询文件切换|schedule, enable
|master-slave-heartbeat|@every 10s|backend|                 | 无               |同步心跳|schedule, enable
|routine-definer|0 0 15 \* \* 1|backend|                 | 预警              |存储过程 definer 存在, 且 host 必须为 localhost|schedule, enable
|view-definer|0 0 15 \* \* 1|backend|                 | 预警              |视图 definer 存在, 且 host 必须为 localhost|schedule, enable
|trigger-definer|0 0 15 \* \* 1|backend|                 | 预警              |触发器 definer 存在, 且 host 必须为 localhost|schedule, enable
|engine|0 0 12 \* \* 1|backend|                 | 预警              | 引擎混用检查以及非系统表是否有 myisam 引擎|schedule, enable
|mysql-config-diff | @every 10m | backend |                 | 预警              |配置文件和运行时变量一致性|schedule, enable
|mysql-inject | @every 1m | backend |                 | 致命              |注入检查|schedule, enable
|mysql-lock | @every 1m | backend |                 | 致命              |锁等待|schedule, enable
|mysql-err-critical|@every 1m|backend|                 | 致命              |致命错误日志|schedule, enable
|mysql-err-notice|@every 1m|backend|                 | 预警              |预警错误日志|schedule, enable
|mysql-connlog-size|0 0 12 \* \* \*|backend|                 | 预警              |连接日志大于 4G 自动关闭记录连接日志|schedule, enable
|mysql-connlog-rotate|0 30 23 \* \* \*|backend|                 | 无               |切换连接日志表|schedule, enable
|mysql-connlog-report|0 40 23 \* \* \*|backend|                 | 无               |上报连接日志|schedule, enable
|proxy-user-list|0 0 14 * * 1|proxy|                 | 致命              |proxy 白名单配置文件和运行时一致性|schedule, enable
|proxy-backend|0 0 14 * * 1|proxy|                 | 致命              |proxy backend 配置文件和运行时一致性|schedule, enable
|db-up|@every 10s|backend, proxy|                 | 致命              |db 连通性. 硬编码, 不可配置, 无需录入配置系统|enable
|mysql_monitor_heart_beat|@every 10s|backend, proxy|                 | 无               |监控心跳. 硬编码, 不可配置, 无需录入配置系统|enable

## 生成dbconfig 配置
```
perl config2sql.pl | sed  's/"enable":"1"/"enable":true/g'
```

## 重要
* `character-consistency, ext3-check, *-definer, engine` 不要在 _spider_ 执行
* `ext3-check` 没有意义
* `engine` 单独检查也没有意义
* 其他 _2_ 个要以中控的结果做全集群对比, 是外围建设工具