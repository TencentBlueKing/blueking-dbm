# common-cluster-base-info

查询 DBM 数据库集群基本信息。

## 功能

根据业务 ID、集群域名、IP 列表或实例列表查询集群基础信息，返回集群域名、业务、地域、类型、状态、DBA 等。

这是一个基础 skill，其他 skill 在需要确认集群信息时会先通过 AGENTS.md 触发本 skill。

## 目录结构

```
common-cluster-base-info/
└── SKILL.md          # skill 主文件
```

## 使用的 MCP 接口

| 接口 | 用途 |
|---|---|
| `dbmeta_query_list_clusters_base_info` | 查询集群基本信息 |

## 依赖

无，本 skill 是最基础的查询 skill。
