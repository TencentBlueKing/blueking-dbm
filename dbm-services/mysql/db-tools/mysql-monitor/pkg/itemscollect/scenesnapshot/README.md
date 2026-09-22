## scene-snapshot 说明
`scene-snapshot` 做两件事：
1. **现场快照**：定期把 `processlist` 和 `show engine innodb status` 存到本地，用于事后排查。支持按需自动触发采集
2. **query-kill**：按规则 kill 掉异常请求，用于止损

两个功能共用一次 `processlist` 查询，执行顺序是 `采集快照 -> kill`，保证被 kill 的请求一定留下了现场。

### 落盘位置
快照按 `场景.端口.日期` 分目录，每轮采集一个 gz 文件：
```
$INSTALL_PATH/scenes/
├── processlist.20000.20260923/
│   ├── 20260923121345.gz
│   └── 20260923121547.gz
└── engine-innodb-status.20000.20260923/
    └── 20260923121345.gz
```
查看：`zcat scenes/processlist.20000.20260923/20260923121345.gz`

过期目录在**产生新快照时**顺带清理，保留 `snapshot_keep_days` 天。

### 快照选项

|选项|默认|说明|
|-----|-----|-----|
|`snapshot_on_demand`|false|是否按需采集。`false` 为每轮都采集|
|`snapshot_keep_days`|2|快照保留天数|
|`snapshot_long_query_time`|30|按需采集条件：存在 `Time` 大于 N 秒的查询|
|`snapshot_long_query_exclude_user`|[]|判断长查询时忽略这些 user，精确匹配，忽略大小写|
|`snapshot_threads_running`|50|按需采集条件：`Threads_running` 超过 N|
|`snapshot_free_connections`|10|按需采集条件：`max_connections` 剩余可用连接少于 N|

两个按需条件是 **or** 关系，命中任一即采集。判断长查询时会自动跳过 `Sleep` 空闲连接、复制线程(`system user`)、`Binlog Dump`，这些连接的 `Time` 天然很大。

- 示例 1：默认行为，每分钟都留一份现场，保留 2 天
```yaml
- name: scene-snapshot
  enable: true
  schedule: '@every 1m'
  options:
    snapshot_on_demand: false
    snapshot_keep_days: 2
```

- 示例 2：只在实例有异常时才采集，降低磁盘开销
```yaml
  options:
    snapshot_on_demand: true
    snapshot_keep_days: 2
    snapshot_long_query_time: 30
    snapshot_threads_running: 50
    # 备份、校验这类后台任务跑很久是正常的，不作为采集依据
    snapshot_long_query_exclude_user:
      - dba_bak
      - MONITOR
```

主要解决的场景：慢查询还没来得及写进 slowlog，实例就已经被打挂/重启了，事后连 SQL 都拿不到。

### query-kill 选项
* kill query 功能一定要跟业务确认影响，以及记得关闭。仅限紧急情况下使用 **

|选项|默认|说明|
|-----|-----|-----|
|`query_kill_enable`|false|总开关，**必须显式打开**|
|`query_kill_max_per_round`|0|全局上限，单轮所有规则合计最多处理 N 个连接，0 不限制|
|`query_kill_rules`|[]|规则列表|

单条规则支持的字段：

|字段|匹配方式|说明|
|-----|-----|-----|
|`rule_name`|-|规则名，只用于日志，不填自动生成 `query-kill-rule-<下标>`|
|`match_db`|精确，忽略大小写|库名|
|`match_user`|精确，忽略大小写|用户名|
|`match_host`|精确/通配，忽略大小写|来源 ip。逗号分隔多个，`%` 通配，命中任一即可|
|`match_command`|精确，忽略大小写|如 `Sleep`、`Query`|
|`match_state`|精确，忽略大小写|如 `Sending data`|
|`match_query`|**正则，大小写敏感**|执行的 SQL|
|`time_gt`|-|`Time` 大于 N 秒|
|`action`|-|`kill` / `print`，默认 `kill`。`print` 只记录不执行|

规则语义：
* 同一条规则内的多个 `match_*` 是 **and** 关系
* 多条规则之间是 **or** 关系，一个连接命中第一条即处理，不会被重复 kill
* **所有条件都为空的规则会被丢弃**，避免误杀全部连接
* 非法规则（正则编译失败、`action` 不认识）只丢弃该条，不影响其他规则和快照采集
* 永不处理：当前监控自身连接、复制线程(`system user`)、`event_scheduler`、`Binlog Dump`、`Daemon`、`Connect`

- 示例 1：紧急 kill 掉有问题的查询
```yaml
  query_kill_rules:
    - rule_name: bad-query-groupby-kill-xxxx
      match_command: Query
      match_query: '^(?is)select\s.*XXTable.*group by'
      time_gt: 60
    - rule_name: select-sleep-kill
      match_command: Query
      match_query: '^select\s+sleep\s*\('
      time_gt: 60
    - rule_name: bad-alter-table
      match_state: Waiting for table metadata lock
      match_query: '^alter table XXTable'
      time_gt: 10
```

- 示例 2：先用 `print` 观察，确认命中范围符合预期再改成 `kill`（**强烈建议**）
```yaml
  options:
    query_kill_enable: true
    query_kill_rules:
      - rule_name: long-sleep
        match_command: Sleep
        time_gt: 3600
        action: print
```

命中记录在 `mysql-monitor.log` 里搜 `query kill hit process`。

- 示例 3：清理长时间空闲连接，并限制单轮最多 kill 20 个
```yaml
  options:
    query_kill_enable: true
    query_kill_max_per_round: 20
    query_kill_rules:
      - rule_name: long-sleep
        match_user: report_ro
        match_host: 1.1.1.1,1.1.1.2,1.2.%
        match_command: Sleep
        time_gt: 7200
        action: kill
```

**注意：**

- `match_query` 是**正则**且**大小写敏感**，需要忽略大小写请自己加 `(?i)` 前缀.
  在 yaml 中配置，字符串用 `''` 括起来，用`""` 会导致`\s`当做转义而不是代表空格类字符。
- `match_query` 是**子串搜索**，不是全串匹配。配 `sleep` 会同时命中 `select * from sleeping_logs`，
  要精确限定请用 `^` / `$` / `\b` 锚定，比如 `'^\s*select\s+sleep\s*\('`
- 其余 `match_*` 字段都是**精确相等**，不是子串也不是正则。
  `match_db: test` 不会命中 `test_db`，`match_state: Sending data` 不会命中 `Sending data to client`
- 在 yaml 里写正则请用**单引号** `'`，双引号 `"` 会把 `\s` `\b` 当未知转义符报错
- `match_host` 只比较 ip 部分（`processlist` 里是 `ip:port`，端口是随机的）。
  `%` 只是通配符，`.` 按字面处理，`1.1.1.%` 不会命中 `1x1x1x1`
- `action` 默认是 `kill`，规则不写 `action` 就会真的 kill
- `time_gt` 如果小于 schedule 间隔，要等 schedule 触发执行后才会检查 kill rule.
   也可以手动循环跑:
```
./mysql-monitor run --items scene-snapshot -c monitor-config_20000.yaml --no-delay
```
