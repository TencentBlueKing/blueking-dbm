# 告警类型: MySQL 主机磁盘空间使用率过高

## 告警解释

MySQL 主机的磁盘空间使用率持续超过阈值（通常 ≥ 90%），说明实例所在主机的存储资源即将耗尽，可能导致：
- MySQL 无法写入新数据，事务提交失败
- binlog 无法正常写入，主从复制中断
- 备份任务失败
- 严重时 MySQL 进程 crash

常见原因：
- 业务数据持续增长，未及时扩容
- 某些表短时间内数据量暴增（如日志表、临时表）
- binlog 积压过多未清理
- 备份文件未及时清理（/data/dbbak 目录）
- 大事务产生大量 undo log
- 非 DB 相关文件占用（安装包、core 文件、人工遗留的大文件等）

**核心关注点**：以主机实际目录扫描（Step 2）为依据，确认磁盘占用是由 **datadir / binlog 目录 / 备份目录 / 非 DB 相关目录** 中的哪一类引起，再定位增长最快的库/表与超大文件。

## 背景知识

DBM MySQL 的数据目录格式一般为：
- **多分区场景**：`/data1/mysqldata/<port>` — datadir、binlog_dir、backup_dir 分别在不同分区
- **单分区场景**：datadir (`/data/mysqldata/<port>`)、binlog_dir (`/data/mysqllog/<port>`)、backup_dir (`/data/dbbak/<port>`) 共用 `/data` 分区

单分区场景下，磁盘空间告警可能由以下任一目录引起：
- `/data/mysqldata` — 数据文件增长（`<port>/data/<dbname>` 为各库目录，`<port>/innodb/{data,log}` 为共享表空间与 redo）
- `/data/mysqllog` — binlog 积压（`<port>/binlog`）
- `/data/dbbak` — 备份文件未清理
- **非 DB 相关目录** — `/data/install`、`/data/nmon_re`、`/home/mysql`、`/data/home/*`、`/tmp` 等人为遗留的大文件

⚠️ **不要仅凭库表大小下结论**：库表大小之和只反映 datadir，binlog / 备份 / 非相关文件的占用必须通过 Step 2 的磁盘目录扫描确认。

## 关键字段提取

从告警维度中提取以下关键信息：

| 字段 | 来源 | 说明 |
|------|------|------|
| `target_ip` | `目标` 或 `目标IP` 维度 | 告警主机 IP（`目标` 形如 `21.160.102.124_mysql-backend_20000` 时取首段 IP） |
| `cluster_domain` | `cluster_domain` 维度 | 集群域名 |
| `instance_role` | `instance_role` 维度 | 实例角色（如 backend_slave） |
| `bk_scope_id` | `所属空间` 中的 `[数字]`（如 `[1234]XX业务` → `1234`） | CMDB 业务 ID，调用 `bkjob-wrap` 必填 |
| `cluster_type` | `cluster_type` 维度或从告警上下文推断 | 集群类型（tendbha / tendbcluster） |
| `mount_point` | `mount_point` 维度 | 告警磁盘挂载点（如 /data、/data1） |
| `current_value` | `内容` 字段中的 `当前值` | 当前磁盘使用率 |

## 分析步骤

### Step 1: 查看磁盘空间趋势

#### Step 1.1 查看磁盘使用率变化趋势（过去 7 天）

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "disk_usage", "start_time": "<base_time - 7d>", "end_time": "<base_time>"}' \
  --raw-query "<用户原始问题>"
```

**分析要点**：
- 磁盘使用率是缓慢上升还是突然飙高
- 7 天内增长了多少百分点
- 是否在某个时间点出现拐点（对应可能的触发事件）
- 按当前增长速度预估何时会达到 100%

#### Step 1.2 查看磁盘使用量变化趋势（过去 7 天）

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "disk_used", "start_time": "<base_time - 7d>", "end_time": "<base_time>"}' \
  --raw-query "<用户原始问题>"
```

**分析要点**：
- 7 天内磁盘使用量增长了多少 GB
- 日均增长量是多少
- 是否存在突增（某天增长量远超平均值）

### Step 2: 上机器看下当前磁盘空间目录占用

**调用方式为异步两步**：先下发作业拿 `job_instance_id`，再查询作业结果。

#### 2.1 下发磁盘目录统计作业

```bash
dbm-mcp-cli call bkdbm-mcp-prod-bkjob-wrap.bkjob_wrap_mysql_query_disk_dir_size \
  body_param='{"bk_scope_id": "<bk_scope_id>", "bk_scope_type": "biz", "bk_cloud_id": <bk_cloud_id>, "ips": ["<target_ip>"]}' \
  --raw-query "<用户原始问题>"
```

参数说明：

| 参数 | 类型 | 说明 |
|------|------|------|
| `bk_scope_id` | **字符串** | CMDB 业务 ID，取告警 `所属空间` 的 `[数字]`（⚠️ 不是 `appid`，不是 DBM 内部业务 ID） |
| `bk_scope_type` | 字符串 | 固定 `"biz"`（⚠️ 禁止 `biz_set`） |
| `bk_cloud_id` | 整数 | 云区域 ID，默认 `0`；非直连区域从 `mysql_query_mysql_cluster_topo` 结果中取 |
| `ips` | 数组 | 目标 IP 列表，填 `target_ip`；同集群多台机器可一次传入 |

返回示例（仅返回作业 ID，**不含**统计结果）：

```json
{"data": {"job_instance_id": 45081765291, "bk_scope_type": "biz", "bk_scope_id": "5005578"}, "result": true}
```

#### 2.2 查询作业执行结果

等待约 10 秒后查询（⚠️ 此处 `bk_scope_id` 为**整数**类型）：

```bash
dbm-mcp-cli call bkdbm-mcp-prod-bkjob-wrap.bkjob_wrap_query_result \
  body_param='{"bk_scope_id": <bk_scope_id>, "bk_scope_type": "biz", "job_instance_id": <job_instance_id>}' \
  --raw-query "<用户原始问题>"
```

结果判断：

| 字段 | 含义 |
|------|------|
| `job_finished: false` | 作业未结束 → 间隔 10 秒重试，最多 6 次（约 1 分钟） |
| `job_finished: true` + `job_status: 3` | 执行成功，读取 `host_results[].log_content` |
| `job_status` 其它值 | 执行失败/超时 → 在报告中说明"磁盘目录明细获取失败"，继续用 Step 1/3/4 数据分析，不要中断 |
| `host_results[].status: 9` + `exit_code: 0` | 该 IP 执行成功 |

#### 2.3 解析 `log_content`

`log_content` 是纯文本输出.

**分析要点**：
- **对比 `mysqllog` 与 `mysqldata` 的占比**：若 binlog 目录反超数据目录，则根因是 **binlog 积压**（如 `926G /data/mysqllog` vs `318G /data/mysqldata`），应优先核查 binlog 保留策略 / 备份是否卡住 / 从库是否长期未拉取
- **`dbbak` 是否异常大**：备份文件未清理
- **非 DB 相关目录**：`/data/install`、`/data/nmon_re`、`/home/mysql`、`/data/home/*`、`/tmp`、core 文件目录（`/data/corefile`）等占用是否异常，属于可安全清理的部分
- **一级子目录之和 vs 分区已用量**：差值大说明存在已删除但未释放的文件句柄（进程仍持有）或隐藏目录
- **超大单文件**：结合 `#P#p<日期>` 分区名判断是否为按日/按月分区表，是否可归档旧分区
- 多 `<port>` 目录说明单机多实例，需说明每个实例各自占用

### Step 3: 查看各数据库大小

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-capacity.mysql_query_db_size \
  body_param='{"cluster_domain": "<cluster_domain>", "bk_biz_id": <bk_biz_id>}' \
  --raw-query "<用户原始问题>"
```

**分析要点**：
- 哪个数据库占用空间最大
- 各数据库的大小分布是否合理
- 是否有异常大的数据库（如临时库、日志库）

### Step 4: 查看 Top 20 大表

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-capacity.mysql_query_table_size \
  body_param='{"cluster_domain": "<cluster_domain>", "bk_biz_id": <bk_biz_id>, "top_n": 20}' \
  --raw-query "<用户原始问题>"
```

注意：`database_name` 不传或传空，直接按所有表大小排序取前 20。

**分析要点**：
- 哪些表占用空间最大
- 大表是否集中在某个数据库
- 是否有日志类/流水类表（通常增长最快）
- 表的数据大小 vs 索引大小比例是否合理

## 报告输出格式

### 磁盘空间趋势（过去 7 天）

| 指标 | 7天前 | 当前值 | 增长量 | 日均增长 | 趋势 |
|------|-------|--------|--------|---------|------|
| 磁盘使用率 | xx% | xx% | +xx% | +xx%/天 | 缓慢上升/突增/稳定 |
| 磁盘使用量 | xx GB | xx GB | +xx GB | +xx GB/天 | 缓慢上升/突增/稳定 |

趋势描述：用文字说明磁盘增长模式，是否存在突增时间点，按当前趋势预估多久会打满。

### 磁盘目录占用明细（来自主机实际扫描）

**告警分区概况**

| 分区 | 设备 | 总容量 | 已用 | 可用 | 使用率 |
|------|------|--------|------|------|--------|
| /data | /dev/nvme0n1 | 3.5T | 1.3T | 2.1T | 38% |

**一级目录占用（按大小排序）**

| # | 目录 | 大小 | 占分区已用 | 类别 |
|---|------|------|-----------|------|
| 1 | /data/mysqllog | 926G | 71% | binlog |
| 2 | /data/mysqldata | 318G | 24% | datadir |
| 3 | /data/dbbak | 44M | ~0% | 备份 |
| 4 | /data/install | 1.3G | ~0% | 非 DB 相关 |

> 类别列必须明确标注：`datadir` / `binlog` / `备份` / `非 DB 相关`，便于直接看出占用归属。

**关键目录深度扫描**

| 目录 | 大小 | 说明 |
|------|------|------|
| /data/mysqllog/20000/binlog | 925.2G | 实例 20000 的 binlog |
| /data/mysqldata/20000/data/<db> | xx G | 库级数据目录（列 Top N） |
| /data/mysqldata/20000/innodb/{data,log} | xx G | 共享表空间 / redo |

**超大文件（> 20G）**

| # | 文件 | 大小 |
|---|------|------|
| 1 | /data/mysqldata/20000/data/zk_rule_engine/judgestep#P#p20260825.ibd | 85.7G |

> 若 Step 2 作业执行失败或超时，此节写明"磁盘目录明细获取失败（原因）"，并说明后续结论仅基于监控指标与库表大小。

### 数据库大小分布

| # | 数据库名 | 大小 | 占比 |
|---|---------|------|------|
| 1 | ... | xx GB | xx% |
| 2 | ... | xx GB | xx% |
| ... | ... | ... | ... |

### Top 20 大表

| # | 数据库 | 表名 | 数据大小 | 索引大小 | 总大小 |
|---|--------|------|---------|---------|--------|
| 1 | ... | ... | xx GB | xx GB | xx GB |
| 2 | ... | ... | xx GB | xx GB | xx GB |
| ... | ... | ... | ... | ... | ... |

### ⚠️ 磁盘分区说明

结合告警 `mount_point` 与 Step 2 实际扫描结果判断分区情况（**以扫描结果为准**，告警维度仅作参考）：
- `mount_point` 为 `/data` 且扫描到 `mysqldata`、`mysqllog`、`dbbak` 都在该分区下：单分区模式，需按目录占用判断根因
- `mount_point` 为 `/data1` 且该分区下只有 `mysqldata`：多分区模式，磁盘增长主要由数据文件引起
- 扫描结果显示 datadir/binlog_dir 分属不同设备（对比各分区的 `[Real Device]`）：以告警分区所含目录为分析对象，其它分区不背锅

### 综合结论

根据以上多维度数据，综合分析：
1. **磁盘空间增长的主要原因**，必须由 Step 2 的目录占用明细直接给出归因，并说明占比：
   - binlog 积压（`mysqllog` 占比最高）→ 核查 binlog 保留天数配置、备份任务是否正常、从库是否长期未消费、是否有大量写入导致 binlog 暴涨
   - 数据文件增长（`mysqldata` 占比最高）→ 结合 Step 3/4 定位库表
   - 备份未清理（`dbbak` 占比高）→ 核查备份清理策略
   - 非 DB 相关文件（`install` / `nmon_re` / `home` / core 文件等占比高）→ 可优先清理
2. 增长最快的库/表是什么，是否存在 > 20G 的超大表/分区文件
3. 按当前增长速度，预计多久会达到危险水位（98%）或打满（100%）
4. 建议的处理措施（按优先级排列）：
   - 紧急：是否需要立即清理空间（清理过期备份、purge binlog、清理非 DB 相关大文件 / core 文件）
   - 短期：是否需要对大表进行数据归档，或调整 binlog 保留策略
   - 长期：是否需要扩容磁盘或迁移到更大规格的主机，改成分区表，或者使用字段压缩
5. 是否需要进一步人工介入
6. 任何情况下都不要建议用户删表，或者删除数据，这会导致数据丢失。

