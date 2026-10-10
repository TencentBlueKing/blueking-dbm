# DBM MySQL 名词解释

## 平台
- **DB** 是数据库的简称，但 **DBM** 指的是互娱数据库管理平台 (dbm.woa.com)

## 集群类型 (cluster_type)

DBM 上有 3 种 MySQL 架构：

| 集群类型 | 说明 | 域名特征 |
|---------|------|---------|
| tendbsingle | MySQL 单节点 | `xxxdb.yyy.zzz.db` |
| tendbha | MySQL 主从 | `xxxdb.yyy.zzz.db` |
| tendbcluster | MySQL 分布式集群（也叫 tspider） | `spider.yyy.zzz.db` |

## 存储层 / 后端

存储层和后端是同一个概念：

| 集群类型 | 机器类型 | 角色 |
|---------|---------|------|
| tendbha | backend | backend_master, backend_slave |
| tendbcluster | remote | remote_master, remote_slave |

## 接入层 / Proxy

接入层和 proxy 是同一个概念：

| 集群类型 | 机器类型 | 角色 |
|---------|---------|------|
| tendbha | proxy | （无特定角色区分） |
| tendbcluster | spider | spider_master, spider_slave |

## 其他概念

- **业务**: app, biz, app_id, bk_biz_id 都是指 DBM 中的业务
- **集群**: 一般指集群域名 (cluster_domain)，所有 DB 集群域名以 `.db` 结尾
- **实例 (instance)**: MySQL 实例，用 `ip:port` 表示

## 如何判断实例类型

- 如果用户提到实例是 tendbha 的 **proxy**，或者明确说是接入层 proxy，应使用 `mysql_query_show_proxy_processlist`
- 其他情况（存储层实例、单节点、分布式后端等），应使用 `mysql_query_show_mysql_processlist`
