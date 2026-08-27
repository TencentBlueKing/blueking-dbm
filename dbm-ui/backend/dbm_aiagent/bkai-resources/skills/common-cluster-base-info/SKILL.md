---
name: common-cluster-base-info
description: 查询集群基本信息（域名、业务、地域、类型等）。当用户提供集群域名、IP 列表或实例地址查询集群信息时触发。
metadata: {"version":"1.0.5","space_id":"1d3d86fa67bef8c3","bk_skill_code":"common-cluster-base-info","is_public":false,"bkai-dependencies":{"envs":[{"key":"DBM_MCPS","description":"dbm mcp server 地址列表","required":true,"default":"bkdbm-mcp-prod-dbmeta-query","secret":false},{"key":"OUTPUT_DIR","description":"skills 产物输出路径","required":false,"default":".storage/session","secret":false}]}}
---

# 集群信息查询技能

## 核心功能
查询DBM数据库集群的基础信息，支持按集群域名、IP列表或实例列表进行查询。
同时支持连接情况分析，包括连接泄漏排查和真实来源IP追溯。

## 触发条件
当用户表达以下意图时触发：
- 查询集群基本信息
- 查集群详情
- 查看集群列表

## 工作流程

### 1. 参数提取
从用户输入中提取以下结构化字段：
- `cluster_domains`: 集群域名 (字符串数组，可选)
- `ips`: IP列表 (字符串数组，可选)
- `instances`: 实例列表，格式为"ip:port" (字符串数组，可选)

**重要**：未提及的可选字段不要传递，只传递用户明确提供的信息。

### 2. 参数验证
- 验证IP格式和实例格式(ip:port)
- `cluster_domain, ips, instances` 不能同时为空

### 3. 工具调用
使用以下格式调用工具：

```bash
dbm-mcp-cli call bkdbm-mcp-prod-dbmeta-query.dbmeta_query_list_clusters_base_info body_param='{"cluster_domains": ["example.com"]}' --raw-query "<用户原始问题>"
```

**关键约束**：
- 所有参数必须包裹在 `body_param` 中
- 禁止将用户原始语句直接塞入参数值
- 使用JSON格式，确保字段名和类型正确

### 4. 结果处理
解析返回数据，按以下格式逐条展示，每个集群之间空一行：

以 Markdown 表格格式输出：

| 集群域名 | 业务ID | 地域 | 类型 | 状态 | DBA |
|---------|--------|------|------|------|-----|
| ... | ... | ... | ... | 正常/异常 | ... |

- status 为 normal 显示"正常"，其他显示"异常: " + 原始值
- DBA 多人用逗号拼接
- 结尾汇总一行：`共 N 个集群`
- 如果查询失败，报告错误信息

## 使用示例

**用户输入**: "查询实例192.168.1.1:3306和192.168.1.2:3306的集群信息"
```json
{"instances": ["192.168.1.1:3306", "192.168.1.2:3306"]}
```

**用户输入**: "查询域名是cluster.example.com的集群"
```json
{"cluster_domains": ["cluster.example.com"]}
```

**用户输入**: "查询IP为192.168.1.1,192.168.1.2的集群"
```json
{"ips": ["192.168.1.1", "192.168.1.2"]}
```

## 注意事项
- 可选参数只有在用户明确提及时才传递
