# API 文档索引

## 概述

本目录存放 BK-DBM 对外或对内约定的 HTTP 接口使用说明（与代码实现同步维护）。

## 接口列表

- [mongodb_instance_restart](./mongodb_instance_restart.md)：MongoDB 实例重启 — 滚动重启（Scene / MONGODB_INSTANCE_RELOAD 单据，infos 支持 cluster_id / ip / 显式实例）。
- [mongodb_list_available_versions](./mongodb_list_available_versions.md)：MongoDB 工具箱 — 查询集群可升级版本列表（支持多集群交集）。
- [mongodb_list_cluster_shards](./mongodb_list_cluster_shards.md)：MongoDB 工具箱 — 查询分片集群分片名列表（供缩容分片数下拉 / 预览）。
- [mongodb_reduce_shard_flow](./mongodb_reduce_shard_flow.md)：MongoDB 缩容分片数 — Scene `multi_cluster_reduce_shard`（指定分片 / 指定数量双模式）。
