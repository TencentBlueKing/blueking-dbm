# mysql-cluster-skew-report

查询并分析 TenDBHA/TenDBCluster 集群负载倾斜情况，生成倾斜分析报告。

## 功能

通过 MCP 接口查询集群倾斜数据，自动解读并生成结构化的倾斜分析报告，帮助用户快速定位负载不均问题。

### 分析能力

| 能力 | 说明 |
|------|------|
| 倾斜检测判定 | 根据 `has_skew` 判断查询时段内是否存在倾斜，无倾斜时明确告知 |
| 热点/冷点识别 | 解析每个节点的实际值、组均值、百分比偏离和绝对偏离，定位偏高/偏低节点 |
| 严重程度分级 | 基于偏离百分比（< 50% 轻度 / 50%-100% 中度 / > 100% 严重），并结合绝对偏离量修正判断 |
| 热点模式判断 | 区分热点稳定（fixed）和热点迁移（migrating），解读热点切换记录 |
| 跨指标关联 | 同时间段多指标（如 CPU + QPS）热点一致时指出关联性 |
| 时间维度分析 | 区分单次检测（时间点）与持续倾斜（时间段），识别间歇性倾斜 |

### 支持的指标与角色

| 指标 | 含义 |
|------|------|
| `cpu_summary` | CPU 使用率 |
| `qps_summary` | QPS（每秒查询数） |
| `connections` | 连接数 |
| `memory_usage` | 内存使用率 |
| `disk_used` | 磁盘使用量 |

| 角色 | 含义 |
|------|------|
| `spider_master` | Spider 接入层主节点 |
| `remote_master` | 远程 DB 层主节点 |

## 工作流程

```
用户提供集群域名 + 时间范围
    ↓ dbm-mcp-cli call mysql_query_query_cluster_skew_data
返回倾斜 JSON → 校验 has_skew
    ├─ false → 输出「无倾斜」结论
    └─ true  → 按 columns 解析 rows
        → 是否有 memory_usage / disk_used 倾斜？
        │   └─ 是 → 补充诊断：查拓扑 + 查机器信息 → 对比同角色节点规格
        → 逐事件提取节点偏离数据
        → 判断严重程度（pct + abs_dev 综合评估）
        → 判断热点模式（fixed / migrating）
        → 按归因规则分析原因（DNS/分片/配置差异/异常占用等）
        → 同 metric 多事件合并
        → 跨指标关联分析
        → 生成报告（摘要 + 明细 + 综合分析 + 建议）
        → 上传报告 → 返回 report_id
```

## 使用的 MCP 接口

| 接口 | 用途 | 调用时机 |
|------|------|---------|
| `bkdbm-mcp-prod-mysql-query.mysql_query_query_cluster_skew_data` | 查询集群倾斜数据 | 必须 |
| `bkdbm-mcp-prod-mysql-query.mysql_query_mysql_cluster_topo` | 获取集群拓扑（含 bk_cloud_id） | memory_usage / disk_used 倾斜时 |
| `bkdbm-mcp-prod-dbmeta-query.dbmeta_query_list_machine_info` | 查询机器规格信息 | memory_usage / disk_used 倾斜时 |
| `bkdbm-mcp-prod-ai-report.ai_report_write_report` | 上传报告 | 报告生成后 |

### 倾斜查询接口参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `cluster_domain` | string | 是 | 集群域名 |
| `from_date` | datetime | 是 | 查询起始时间，ISO 8601 格式 |
| `to_date` | datetime | 是 | 查询截止时间，ISO 8601 格式 |

### 返回数据关键字段

| 字段 | 说明 |
|------|------|
| `has_skew` | 是否存在倾斜事件 |
| `period.time_zone` | 集群时区，所有时间均为此时区 |
| `group_mean` | episode 内该 role 组所有节点的均值代表值 |
| `hot_nodes` / `cold_nodes` | 节点详情，每条格式 `ip:port value=X mean=Y pct=±Z% abs_dev=W`，多条以 `;` 分隔 |
| `transitions` | 热点切换记录，格式 `HH:MM→ip:port,...`，仅 `migrating` 模式有值 |

## 倾斜归因规则

| 场景 | 可能原因 | 诊断动作 |
|------|---------|---------|
| 接入层连接数倾斜 | DNS 缓存集中 / 业务直连 IP | 建议换 CLB 或控制连接创建速率 |
| 接入层 QPS/CPU 倾斜 | 长连接负载差异 / 短连接模块差异 | — |
| 接入层磁盘倾斜 | 临时文件（大查询排序、未清理日志） | — |
| 内存倾斜（任意层级） | 机器配置不一致 / 异常内存占用 | 查拓扑 + 查机器规格对比 |
| 存储层磁盘倾斜 | 分片不合理 / 配置差异 / 备份未清理 / 临时文件 | 查拓扑 + 查机器规格对比 |
| 存储层连接/QPS/CPU 倾斜 | 数据分片不合理 | 检查分片键和热点 shard |

## 报告结构

| 章节 | 内容 |
|------|------|
| 结论摘要 | 是否倾斜、涉及指标、主要热点、是否发生热点迁移 |
| 倾斜事件明细 | 按 metric/role 分组，含节点明细表（实际值、组均值、偏离度、绝对偏离） |
| 综合分析 | 跨指标关联、时间维度总结 |
| 原因分析与建议 | 按归因规则给出针对性分析，含机器配置对比结果（如适用） |

## 目录结构

```
mysql-cluster-skew-report/
├── SKILL.md          # skill 主文件（工作流程、数据格式、解读规则、报告模板）
└── README.md         # 本文件
```

## 依赖

- `common-cluster-base-info`：由 AGENTS.md 在进入本 skill 前自动调用，提供 `cluster_domain`
