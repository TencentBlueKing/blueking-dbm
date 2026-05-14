# MongoDB 亲和性检查说明

本文档是 MongoDB 亲和性巡检的唯一口径文档，覆盖离线脚本与线上周期任务。

## 1. 规则来源

- 枚举与中文标签：`backend/configuration/constants.py` 中 `AffinityEnum`
- 规则原始注释：`affinity_rule.md`

## 2. 检查对象

- `MongoReplicaSet`
- `MongoShardedCluster`
  - `mongos`
  - `configsvr`
  - `shardsvr`（按机器组聚合，非按 set_name）

## 3. 离线输入数据

- `cluster_defs.json`：`cluster_region`、`disaster_tolerance_level`、`zone_list` 等
- `cluster_nodes.json`：`set_name`、`ip:port`、`instance_role`、`bk_sub_zone_id`、`bk_rack_id`、`bk_city_id`
- `subzones.json`：每条含 `bk_sub_zone_id`、`bk_sub_zone`；**亲和性 region 仅使用非空的 `logical_city_name`**（与 `Cluster.region` / `LogicalCity.name` 同口径）。可选带 `bk_idc_city_name` 仅供人工核对，不参与 region 解析。
- `cities.json`：每条含 `bk_city_id`；**必选非空 `logical_city_name`** 用于 region 映射。可选 `bk_idc_city_name` 仅供人工核对。

可用 `dbm-ui/.cycscript/dump_affinity_json.sh` 从正式环境 MySQL 导出上述 JSON（仅需 `mysql` 客户端、`python3` 标准库与环境变量 `MYSQL_*`，**不依赖** Django / 本仓库 Python 代码）。

## 4. 通用校验前置

- 节点必须具备 `bk_sub_zone_id` 与 `bk_rack_id`
- 非 `NONE` 场景下：
  - 节点必须可解析到 region（**仅**逻辑城市名：线上为 `Machine.bk_city.logical_city.name`，离线为 `cities`/`subzones` 中的 `logical_city_name`）
  - 组件节点必须单 region
  - 组件 region 必须与 `cluster.region` 一致

**命名说明（昆山 / 上海等）：** `cluster.region` 常为逻辑城市名（如「上海」），机器侧 CMDB 城市名可能为 IDC 粒度（如「昆山」）。在业务归属一致的前提下，**歧义纯粹来自命名粒度不统一，并非部署拓扑错误**。比对统一以逻辑城市（`LogicalCity.name` / 离线 `logical_city_name`）与 `cluster.region` 对齐，避免因名不同而误报 `region_mismatch`。

## 5. 成员数检查

- `mongos` 至少 `2` 个成员
- `replicaset / configsvr / shardsvr组` 至少 `3` 个成员
- 集群标签 `single_node:true`（离线 JSON `has_single_node_tag`）时：跳过成员数检查；**同时**在 `check_affinity_rules` 内跳过下列亲和性等级的**最小子区域数**约束（其它规则如 region、zone_list、园区容忍度、rack 等仍执行）：
  - `CROS_SUBZONE`：不校验「至少 2 个 sub_zone」
  - `CROSS_SUBZONE_STRONG`：不校验「至少 3 个 sub_zone」的园区数量下限（`zone_tolerance` 等仍校验）
  - `CROSS_SUBZONE_WEAK`：不校验「至少 2 个 sub_zone」的园区数量下限（`zone_tolerance` 等仍校验）
  - `MAJORITY_ELECTION_DISTRI`：不校验「至少 2 个 sub_zone」

## 6. zone_list 规则

- `SAME_SUBZONE` / `SAME_SUBZONE_CROSS_SWTICH`：
  - `zone_list` 必填且仅 1 个值（配置错误）
- 其他非 `NONE`：
  - `zone_list` 可为空
  - 若不为空，需与实际 `sub_zone` 集合一致

## 7. 各亲和性等级口径

### SAME_SUBZONE

- 单 `sub_zone`

### SAME_SUBZONE_CROSS_SWTICH

- 仅非 backup 节点参与核心校验
- 非 backup 必须单 `sub_zone`
- 非 backup 至少跨 `2` 个 `rack`
- backup 可在 `zone_list` 指定 sub_zone 之外

### CROS_SUBZONE

- 至少 `2` 个 `sub_zone`

### CROSS_SUBZONE_STRONG

- 至少 `3` 个 `sub_zone`
- zone 容忍度：任一 zone 节点数不超过 `ceil(n/3)`
- rack 校验按组件整体计算（合并所有 sub_zone）：
  - 至少 `2` 个 rack
  - 任一 rack 节点数不超过 `ceil(n/2)`

### CROSS_SUBZONE_WEAK

- 至少 `2` 个 `sub_zone`
- zone 容忍度：任一 zone 节点数不超过 `ceil(n/2)`
- rack 校验按组件整体计算（合并所有 sub_zone）：
  - 至少 `2` 个 rack
  - 任一 rack 节点数不超过 `ceil(n/2)`

### MAJORITY_ELECTION_DISTRI

- 至少 `2` 个 `sub_zone`
- 任一 zone 节点数不超过 `ceil(n/2)`
- 同一 rack 不超过 `1` 节点
- zone 分布近似均衡（`max-min <= 1`）

### CROSS_RACK

- 至少 `2` 个 `rack`

### MAX_EACH_ZONE_EQUAL

- zone 分布近似均衡（`max-min <= 1`）

### NONE

- 不做亲和性约束

## 8. ShardedCluster 聚合与输出

- `shardsvr` 按机器组聚合：
  - 组 key：`shardsvr_group:<bk_cloud_id:ip|...>`
  - 聚合后按机器维度去重（同机多分片不重复计数）
- 离线输出中，若仅 `mongos` 异常，仅打印 `mongos` 组件详情

## 9. 输出内容

- 集群总览：`total/success/warning/abnormal`
- 异常/预警明细：
  - 集群级：`cluster_id`、`domain`、`affinity`、`cluster_region`
  - 组件级：`zone_list`、`actual_sub_zones`、`actual_regions`、`actual_racks`
  - 节点级：`instance(addr)`、`actual_sub_zone`、`actual_rack`、`instance_role`
- `reason` 带 `code=...`，离线包含 `domain`
- 离线支持 `--summary-by-code`

## 10. 错误码

- 详见 `error_code_reference.md`

## 11. 最近变更历史

- `SAME_SUBZONE_CROSS_SWTICH` 增加 backup 例外：
  - `instance_role=backup/MONGO_BACKUP` 的节点允许在 `zone_list` 指定 sub_zone 之外
  - 该等级核心约束（单 sub_zone、跨 2 rack）仅对非 backup 节点生效
- `MongoShardedCluster` 的 `shardsvr` 从“按 set_name 检查”调整为“按机器组检查”：
  - 组 key 使用 `shardsvr_group:<bk_cloud_id:ip|...>`
  - 同机多分片场景下，组内按机器维度去重，避免重复计数放大告警
- `CROSS_SUBZONE_WEAK/STRONG` 的 rack 校验从“按 zone 分别计算”调整为“全组件汇总计算”：
  - 将所有 sub_zone 的节点合并后统一校验 rack 数量与 rack 容忍度
  - 与实际“跨 rack”语义保持一致，减少局部 zone 误判
- 地域（region）与 `cluster.region` 对齐：**仅**使用 `BKCity.logical_city.name`（线上巡检与离线 JSON 的 `logical_city_name`），不再用 IDC 城市名参与比对；逻辑城市名为空时记为数据缺失。

