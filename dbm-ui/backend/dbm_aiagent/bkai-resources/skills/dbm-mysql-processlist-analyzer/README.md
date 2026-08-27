# mysql-processlist-analyzer

MySQL processlist 连接分析，支持单实例和集群两种模式。

## 功能

通过 `dbm-mcp-cli` 抓取 MySQL 实例的 processlist 数据，使用 Python 脚本进行多维度聚合分析，并结合活跃连接采样让 LLM 进行补充分析，最终输出诊断报告和处理建议。

## 工作模式

| 模式 | 触发条件 | 流程 |
|------|---------|------|
| 集群模式 | 用户提供集群域名 | 查拓扑 → 逐实例并行抓取 → 合并分析 |
| 单实例模式 | 用户提供 `ip:port` | 直接抓取 → 分析 |

## 分析维度

| 类型 | 说明 |
|------|------|
| `summary` | 概览 + Top 用户/IP/指纹/库 + 最长连接 + 锁等待（默认） |
| `all` | 全部维度（含 state 分布） |
| `group_by_fingerprint` | SQL 指纹聚合 |
| `group_by_state` | 状态分布 |
| `group_by_user` | 用户聚合 |
| `group_by_client_host` | 来源 IP 聚合 |
| `group_by_db` | 库名聚合 |
| `lock_wait` | 锁等待检测 |
| `longest_top_5` | 最长运行查询 |
| `sample` | 活跃连接采样（最多 30 条），供 LLM 自由分析 |

## 目录结构

```
mysql-processlist-analyzer/
├── SKILL.md                              # skill 主文件（工作流、输出格式）
├── scripts/
│   ├── check_mcp_response.py            # 验证 dbm-mcp-cli 响应并提取 processlist 数组
│   └── analyze_processlist.py           # 多维度聚合分析 + 活跃连接采样
└── README.md
```

## 使用的 dbm-mcp-cli 接口

| 接口 | 用途 |
|------|------|
| `mysql_query_mysql_cluster_topo` | 集群模式下获取拓扑（实例列表、角色、集群类型） |
| `mysql_query_show_mysql_processlist` | 抓取 MySQL 实例 processlist |
| `mysql_query_show_proxy_processlist` | 抓取 TenDBHA Proxy 实例 processlist |

## 数据流

```
dbm-mcp-cli call → pl_raw.json (MCP 原始响应)
    ↓ check_mcp_response.py
processlist.json (processlist 数组)
    ↓ analyze_processlist.py --type summary
结构化分析 JSON (overview / top_* / lock_wait / ...)
    ↓ analyze_processlist.py --type sample
活跃连接明细 JSON (最多 30 条，供 LLM 补充分析)
```

## Python 依赖

- `pandas`
